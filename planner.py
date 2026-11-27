"""Lập lịch và kiểm ngân sách bằng quy tắc, không gọi model."""
from dataclasses import asdict, dataclass
from datetime import date, datetime
from functools import cache
from heapq import heappop, heappush
from math import ceil

import config as cfg
from budget import allocate_budget, check_budget, estimate_band
from data_loader import load_data
from lodging import haversine, lodging_options
from weather_service import trip_weather, unavailable

SLOTS = tuple(cfg.SLOT_MINUTES)


@dataclass(frozen=True)
class TripRequest:
    region: str
    days: int
    budget_vnd: int
    people: int = 1
    month: int | None = None
    start_date: date | str | None = None
    style: str = cfg.DEFAULT_STYLE
    budget_scope: str = "per_person"


def _request(raw):
    raw = TripRequest(**raw) if isinstance(raw, dict) else raw
    if (not isinstance(raw, TripRequest) or raw.region not in cfg.REGIONS or raw.style not in cfg.BUDGET_SPLIT
            or type(raw.days) is not int or not 1 <= raw.days <= cfg.MAX_DAYS
            or type(raw.people) is not int or raw.people < 1
            or type(raw.budget_vnd) is not int or raw.budget_vnd <= 0
            or raw.budget_scope not in {"per_person", "total"}):
        raise ValueError("Chọn điểm đến, 1–5 ngày, số người và ngân sách nguyên dương.")
    start = date.fromisoformat(raw.start_date) if isinstance(raw.start_date, str) else raw.start_date
    if start is not None and type(start) is not date:
        raise ValueError("Ngày khởi hành không hợp lệ.")
    month = start.month if start else raw.month
    if type(month) is not int or not 1 <= month <= 12:
        raise ValueError("Nhập ngày khởi hành hoặc tháng từ 1 đến 12.")
    return raw, start, month


def pick_places(region, days, month, style, catalog):
    ticket_costs = {entry["cost_id"]: entry for entry in catalog.costs}
    available = []
    for place in catalog.places:
        price = place["ticket_vnd"]
        if (place["region"] != region or price is None or place["lat"] is None
                or (place["best_months"] and month not in place["best_months"])):
            continue
        cost = ticket_costs.get(place["ticket_cost_id"])
        if cost and cost["category"] == "ticket" and cost["region"] == region and cost["place_id"] == place["place_id"]:
            lower, upper = min(price, cost["price_min_vnd"]), max(price, cost["price_max_vnd"])
            source = cost["source"]
            if not cost["price_min_vnd"] <= price <= cost["price_max_vnd"]:
                source += f"; data/places.csv:{place['place_id']}"
            band = estimate_band(lower, upper, source=source, source_date=cost["source_date"])
        elif not place["ticket_cost_id"] and place["source"]:
            band = estimate_band(price, price, source=place["source"], source_date=place["source_date"])
        else:
            continue
        item = {key: place[key] for key in (
            "place_id", "name", "setting", "setting_is_estimate", "category", "category_is_estimate", "duration_hours",
            "duration_is_estimate", "duration_source", "duration_source_date", "source", "source_date", "rain_sensitive", "lat", "lon",
        )}
        item["ticket"] = band
        item["duration"] = {
            "hours": item["duration_hours"], "is_estimate": item["duration_is_estimate"],
            "source": item["duration_source"], "source_date": item["duration_source_date"],
            "confidence": "low" if item["duration_is_estimate"] else "medium",
        }
        available.append(item)
    return sorted(available, key=lambda item: (
        item["ticket"]["max_vnd"] if style == "tiet_kiem" else 0, item["place_id"]
    ))


def _routes(region, catalog):
    points = {row["place_id"]: row for row in catalog.places if row["region"] == region and row["lat"] is not None}
    graph = {ident: {} for ident in points}
    for row in catalog.routes:
        start, end = row["from_place_id"], row["to_place_id"]
        if row["region"] == region and start in points and end in points:
            existing = graph[start].get(end)
            if existing is None or row["duration_min"] < existing["duration_min"]:
                graph[start][end] = {**row, "symmetric": False}
    for origin, edges in graph.items():
        for target, edge in tuple(edges.items()):
            if origin not in graph[target]:
                graph[target][origin] = {**edge, "symmetric": True}

    @cache
    def leg(start, end):
        if start == end:
            return None
        queue = [(0, start, (), 0)]
        seen = set()
        while queue:
            minutes, position, path, kilometers = heappop(queue)
            if position in seen:
                continue
            seen.add(position)
            if position == end:
                edges = [graph[a][b] for a, b in path]
                sources = sorted({row["source"] for row in edges})
                dates = [row["source_date"] for row in edges if row["source_date"]]
                return {
                    "from_place_id": start, "to_place_id": end,
                    "distance_km": round(kilometers, 1), "duration_min": ceil(minutes),
                    "is_estimate": True, "route_estimated": False,
                    "route_symmetry_is_estimate": any(row["symmetric"] for row in edges), "confidence": "medium",
                    "source": "; ".join(sources), "source_date": min(dates) if len(dates) == len(edges) else None,
                }
            for target, edge in graph[position].items():
                if target not in seen:
                    heappush(queue, (minutes + edge["duration_min"], target, (*path, (position, target)),
                                    kilometers + edge["distance_km"]))
        left, right = points[start], points[end]
        kilometers = haversine(left["lat"], left["lon"], right["lat"], right["lon"])
        return {
            "from_place_id": start, "to_place_id": end, "distance_km": round(kilometers, 1),
            "duration_min": ceil(kilometers * 60 / cfg.FALLBACK_TRAVEL_KMH),
            "is_estimate": True, "route_estimated": True, "confidence": "low",
            "source": "data/places.csv + config.py:FALLBACK_TRAVEL_KMH",
            "source_date": min(left["source_date"], right["source_date"]),
        }

    return points, leg


def _journey(anchor, items, leg):
    points = [anchor, *(item["place_id"] for item in items), anchor]
    legs = [part for start, end in zip(points, points[1:]) if (part := leg(start, end)) is not None]
    return sum(part["duration_min"] for part in legs), legs


def _layout(anchor, places, days, travel_amount, style, leg):
    visited = set()
    schedule = [{"day": index + 1, "items": [], "changed_because": None} for index in range(days)]
    for slot in SLOTS:
        for day in schedule:
            items = day["items"]
            choices = []
            for item in places:
                if (item["place_id"] in visited or item["duration_hours"] * 60 > cfg.SLOT_MINUTES[slot]
                        or item["ticket"]["max_vnd"] > travel_amount):
                    continue
                minutes, _ = _journey(anchor, [*items, item], leg)
                if minutes <= cfg.MAX_TRAVEL_HOURS_PER_DAY * 60:
                    choices.append((item, minutes))
            if choices:
                item, _ = min(choices, key=lambda choice: (
                    choice[0]["ticket"]["max_vnd"] if style == "tiet_kiem" else choice[1],
                    choice[1], choice[0]["ticket"]["max_vnd"], choice[0]["place_id"],
                ))
                items.append({**item, "slot": slot})
                visited.add(item["place_id"])
                travel_amount -= item["ticket"]["max_vnd"]
    return schedule


def _indoors(item):
    return item["setting"] == "indoor" and not item["rain_sensitive"]


def _wet(day):
    weather = day["weather"]
    return weather["source"] == "forecast" and (
        weather["severe"] or (weather["rain_prob"] is not None and weather["rain_prob"] >= cfg.RAIN_THRESHOLD)
    )


def _change_for_weather(schedule, all_places, anchor, leg):
    for day in schedule:
        if not _wet(day):
            continue
        if day["weather"]["severe"]:
            day["items"] = []
            day["changed_because"] = "Dự báo mưa lớn. Tạm hoãn hoạt động và kiểm tra cảnh báo địa phương."
            continue
        original = day["items"]
        day["items"] = [item for item in original if _indoors(item)]
        messages = []
        for item in original:
            if _indoors(item):
                continue
            slot = item["slot"]
            used = {visit["place_id"] for date in schedule for visit in date["items"]}
            candidates = [
                {**option, "slot": slot} for option in all_places
                if _indoors(option) and option["place_id"] not in used
                and option["duration_hours"] * 60 <= cfg.SLOT_MINUTES[slot]
            ]
            viable = []
            for option in candidates:
                ordered = sorted([*day["items"], option], key=lambda visit: SLOTS.index(visit["slot"]))
                minutes, _ = _journey(anchor, ordered, leg)
                if minutes <= cfg.MAX_TRAVEL_HOURS_PER_DAY * 60:
                    viable.append((option, minutes))
            if viable:
                chosen, _ = min(viable, key=lambda choice: (
                    choice[0]["ticket"]["max_vnd"], choice[1], choice[0]["place_id"],
                ))
                day["items"].append(chosen)
                messages.append(f"Đổi {item['name']} sang {chosen['name']}.")
                continue

            moved = False
            for other in schedule:
                if other is day or _wet(other) or other["weather"]["source"] != "forecast":
                    continue
                indoor = next((visit for visit in other["items"] if visit["slot"] == slot), None)
                if indoor and not _indoors(indoor):
                    continue
                wet_items = sorted([*day["items"], indoor], key=lambda visit: SLOTS.index(visit["slot"])) if indoor else day["items"]
                dry_items = sorted(
                    [*(visit for visit in other["items"] if visit is not indoor), item],
                    key=lambda visit: SLOTS.index(visit["slot"]),
                )
                max_minutes = cfg.MAX_TRAVEL_HOURS_PER_DAY * 60
                if max(_journey(anchor, dry_items, leg)[0], _journey(anchor, wet_items, leg)[0]) <= max_minutes:
                    other["items"] = dry_items
                    day["items"] = wet_items
                    if indoor:
                        messages.append(f"Đổi {item['name']} sang {indoor['name']} và dời {item['name']} sang ngày {other['day']}.")
                    else:
                        messages.append(f"Dời {item['name']} sang ngày {other['day']}.")
                    moved = True
                    break
            if not moved:
                messages.append(f"Tạm bỏ {item['name']} vì chưa có phương án trong nhà phù hợp.")
        day["items"].sort(key=lambda visit: SLOTS.index(visit["slot"]))
        if messages:
            percent = format(day["weather"]["rain_prob"], ".0%")
            day["changed_because"] = f"Dự báo mưa {percent}. " + " ".join(messages)


def _charge(category, label, rate, count):
    return {
        **estimate_band(rate["min_vnd"] * count, rate["max_vnd"] * count,
                        source=rate["source"], source_date=rate["source_date"], confidence=rate["confidence"]),
        "category": category, "label": label, "quantity": count,
        "quantity_is_estimate": category in {"food", "transport"},
        "quantity_source": {"food": "config.py:MEALS_PER_DAY", "transport": "config.py:PEOPLE_PER_MOTORBIKE"}.get(category),
    }


def _rate(cost):
    return estimate_band(cost["price_min_vnd"], cost["price_max_vnd"], source=cost["source"], source_date=cost["source_date"])


def _cost_inputs(catalog, region, days, people):
    entries = [row for row in catalog.costs if row["region"] == region]
    meals = [(row, cfg.MEALS_PER_DAY * days * people) for row in entries if row["category"] == "food" and row["unit"] == "per_meal"]
    rentals = [row for row in entries if (row["category"], row["unit"], row["basis"]) == ("bike_rental", "per_day", "vehicle")]
    food = min(meals, key=lambda match: match[0]["price_max_vnd"], default=None)
    rental = min(rentals, key=lambda row: row["price_max_vnd"], default=None)
    food_charge = _charge("food", food[0]["item"], _rate(food[0]), food[1]) if food else None
    return food_charge, rental


def estimate_cost(charges):
    confidence = min((row["confidence"] for row in charges), key=("low", "medium", "high").index, default="low")
    sources = sorted({row["source"] for row in charges})
    dates = [row["source_date"] for row in charges if row["source_date"]]
    totals = estimate_band(
        sum(row["min_vnd"] for row in charges), sum(row["max_vnd"] for row in charges),
        source=sources, source_date=min(dates) if dates else None, confidence=confidence,
    )
    totals["expected_vnd"] = sum(row["expected_vnd"] for row in charges)
    return {**totals, "items": charges}


def _prices(schedule, anchor, leg, selected_lodging, food, rental, people):
    charges = []
    if selected_lodging:
        charges.append({**selected_lodging["predicted_total"], "category": "lodging",
                        "label": selected_lodging["name"], "quantity": selected_lodging["rooms"]})
    if food and schedule:
        charges.append(food)
    traveled_days = sum(_journey(anchor, day["items"], leg)[0] > 0 for day in schedule)
    if rental and traveled_days:
        vehicles = ceil(people / cfg.PEOPLE_PER_MOTORBIKE)
        charges.append(_charge("transport", rental["item"], _rate(rental), traveled_days * vehicles))
    for day in schedule:
        charges.extend(_charge("ticket", item["name"], item["ticket"], people) for item in day["items"])
    return estimate_cost(charges)


def _empty(input_data, region, budget_vnd, allocations):
    return {
        "region": region, "input": input_data, "budget_vnd": budget_vnd,
        "total_cost_vnd": None, "total_cost_range": None, "mode": "itinerary", "days": [],
        "lodging_options": {"budget": [], "mid": [], "comfort": []},
        "lodging_selected": None, "lodging_gap": None, "lodging_unpriced": [], "adjustments": [],
        "warnings": [], "errors": [], "cost_breakdown": [], "budget_allocation": allocations,
    }


def build_plan(request, *, catalog=None, weather=None, today=None):
    """Trả kết quả JSON tuần tự hóa được. weather chỉ dành cho adapter UI và test."""
    try:
        raw, start, month = _request(request)
    except (TypeError, ValueError) as error:
        plan = _empty({}, None, None, {})
        plan["errors"].append({"code": "invalid_input", "message": str(error)})
        return plan
    budget = raw.budget_vnd * raw.people if raw.budget_scope == "per_person" else raw.budget_vnd
    allocations = allocate_budget(budget, raw.style)
    input_data = {**asdict(raw), "start_date": start.isoformat() if start else None, "month": month}
    plan = _empty(input_data, raw.region, budget, allocations)
    today = today or datetime.now(cfg.TIMEZONE).date()
    try:
        catalog = catalog if catalog is not None else load_data()
    except (OSError, ValueError):
        plan["errors"].append({"code": "data_unavailable", "message": "Chưa đọc được dữ liệu đã kiểm tra."})
        return plan

    candidates = pick_places(raw.region, raw.days, month, raw.style, catalog)
    points, leg = _routes(raw.region, catalog)
    anchor = cfg.BASE_PLACES.get(raw.region)
    if anchor not in points:
        anchor = candidates[0]["place_id"] if candidates else None
    nights = raw.days - 1
    schedule = _layout(anchor, candidates, raw.days, allocations["ticket"] // raw.people, raw.style, leg) if candidates else []
    if not any(day["items"] for day in schedule):
        schedule = []
        plan["mode"] = "lodging_only"
        plan["warnings"].append("Chưa đủ điểm tham quan phù hợp với vùng và ngân sách để xếp lịch. Hiển thị phần lưu trú.")
    else:
        try:
            forecasts = weather(raw.region, start, raw.days) if weather else trip_weather(raw.region, start, raw.days, today=today)
        except (OSError, ValueError, RuntimeError):
            forecasts = []
        if not isinstance(forecasts, list) or len(forecasts) != raw.days:
            forecasts = [unavailable(None) for _ in range(raw.days)]
        for day, forecast in zip(schedule, forecasts):
            day["weather"] = forecast
        _change_for_weather(schedule, candidates, anchor, leg)

    itinerary_places = [item for day in schedule for item in day["items"]]
    lodging = lodging_options(catalog, raw.region, nights, raw.people, allocations["lodging"], itinerary_places, today=today)
    plan["lodging_options"] = lodging["groups"] if nights else plan["lodging_options"]
    plan["lodging_gap"] = lodging["cheapest_outside_allocation"] if nights else None
    plan["lodging_unknown_units"] = len(lodging["unpriced"])
    if nights and not lodging["known"]:
        plan["lodging_unpriced"] = lodging["unpriced"][:cfg.MAX_LODGING_OPTIONS]
    if lodging["unpriced"] and nights:
        plan["warnings"].append("Một số chỗ ở chưa rõ đơn vị giá và không được đưa vào phép tính.")
    if nights and not lodging["known"]:
        plan["mode"] = "lodging_only"
        plan["errors"].append({"code": "lodging_unavailable", "message": "Chưa có giá lưu trú đủ căn cứ để tính cho nhóm."})
        return plan

    wanted = {"tiet_kiem": "budget", "vua": "mid", "thoai_mai": "comfort"}[raw.style]
    matched = [item for item in lodging["groups"][wanted] if item["fits_budget"]]
    by_cost = sorted(lodging["known"], key=lambda item: (item["predicted_total"]["max_vnd"], -item["score"], item["price_id"]))
    selected = (matched or by_cost or [None])[0] if nights else None
    cheapest = by_cost[0] if by_cost and nights else None
    if selected and selected["predicted_total"]["expected_vnd"] > allocations["lodging"]:
        plan["warnings"].append("Lưu trú vượt phần phân bổ gợi ý; chỉ giữ nếu cả kế hoạch còn trong trần tổng.")

    food, rental = _cost_inputs(catalog, raw.region, raw.days, raw.people)
    if not food and schedule:
        plan["warnings"].append("Chưa có giá ăn theo bữa cho vùng này; tiền ăn tính riêng.")
    if not rental and schedule:
        plan["warnings"].append("Chưa có giá thuê xe theo ngày; chi phí di chuyển nội vùng chưa tính.")
    if schedule:
        plan["warnings"].append("Giá vé người lớn và tuyến là tham khảo. Đi đến vùng, xăng và tiền cọc tính riêng.")
        if any(day["weather"]["source"] == "unavailable" for day in schedule):
            plan["warnings"].append("Một số ngày chưa có dự báo. Kiểm tra thời tiết, giờ mở cửa và đường trước khi đi.")

    def recompute():
        return _prices(schedule, anchor, leg, selected, food, rental, raw.people)

    def lower_lodging():
        nonlocal selected
        if selected is not cheapest:
            selected = cheapest
            return True
        return False

    def remove_paid():
        changed = False
        while recompute()["max_vnd"] > budget:
            paid = [(day, item) for day in schedule for item in day["items"] if item["ticket"]["max_vnd"] > 0]
            if not paid:
                break
            day, item = max(paid, key=lambda entry: entry[1]["ticket"]["max_vnd"])
            day["items"].remove(item)
            if day["changed_because"]:
                day["changed_because"] += f" Sau kiểm ngân sách, bỏ {item['name']}."
            changed = True
        return changed

    def shorten():
        changed = False
        while recompute()["max_vnd"] > budget:
            traveling = [(day, _journey(anchor, day["items"], leg)[0]) for day in schedule]
            if not any(minutes for _, minutes in traveling):
                break
            day, _ = max(traveling, key=lambda entry: entry[1])
            day["items"] = [item for item in day["items"] if item["place_id"] == anchor]
            if day["changed_because"]:
                day["changed_because"] += " Sau kiểm ngân sách, rút phần di chuyển ngày này."
            changed = True
        return changed

    checked = check_budget(budget, recompute, (
        ("Hạ mức chi cho chỗ ở.", lower_lodging),
        ("Bớt hoạt động có phí.", remove_paid),
        ("Rút ngắn cung đường để giảm số ngày thuê xe.", shorten),
    ))
    estimate = checked["estimate"]
    plan["adjustments"] = checked["adjustments"]
    if not checked["fits_budget"]:
        plan["errors"].append({
            "code": "budget_too_low", "message": "Ngân sách không đủ cho các khoản tối thiểu có dữ liệu.",
            "minimum_required_vnd": estimate["max_vnd"], "minimum_required_range": estimate,
        })
        return plan

    for day in schedule:
        minutes, legs = _journey(anchor, day["items"], leg)
        day["travel_minutes"] = minutes
        day["legs"] = legs
        day["route_estimated"] = any(part["route_estimated"] for part in legs)
        day["slots"] = {slot: next((item for item in day["items"] if item["slot"] == slot), None) for slot in SLOTS}
    plan.update(
        days=schedule, total_cost_vnd=estimate["expected_vnd"], total_cost_range=estimate,
        lodging_selected=selected, cost_breakdown=estimate["items"],
        base_name=points[anchor]["name"] if anchor in points else None,
        data_source=catalog.source,
    )
    return plan
