"""Lập lịch web Việt Du từ dữ liệu có nguồn và kiểm ngân sách theo từng khoản."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from heapq import heappop, heappush
from math import ceil
import re
import unicodedata

from config import MAX_DAYS, MEALS_PER_DAY, PEOPLE_PER_MOTORBIKE, RAIN_THRESHOLD, REGIONS, REGION_NAMES
from lodging import haversine
from vietdu_weather import trip_weather

STARTS = {"ha_giang": ("H01", "H11", "H14"), "da_nang": ("D01", "D02", "D06")}
MODES = {"car": "Ô tô", "motorbike": "Xe máy", "transit": "Xe buýt"}
INTERESTS = {"nature": "Thiên nhiên", "viewpoint": "Ngắm cảnh", "culture": "Văn hóa",
             "food": "Ẩm thực", "market": "Chợ địa phương", "activity": "Trải nghiệm"}
LODGING_TYPES = {"hotel": "Khách sạn", "guesthouse": "Nhà nghỉ", "homestay": "Homestay"}
CATEGORIES = {"ticket": "Vé tham quan", "transport": "Di chuyển", "food": "Ăn uống", "lodging": "Lưu trú"}
DAY_START, DAY_END = 8 * 60, 18 * 60
STOPS_PER_DAY = 3
NEARBY_LODGING_KM = 20  # Sàng lọc theo đường chim bay, không phải quãng đường đi.
HOURS = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:h]([0-5]\d)\s*[-–—]\s*([01]?\d|2[0-4])[:h]([0-5]\d)(?!\d)")


@dataclass(frozen=True)
class Request:
    region: str
    departure: date
    days: int
    people: int
    budget: int
    mode: str = "car"
    origin: str = ""
    interests: tuple[str, ...] = ()
    lodging_type: str = ""
    allowances: dict = field(default_factory=dict)

    @classmethod
    def parse(cls, payload, today):
        def integer(value, minimum, maximum, label):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{label} không hợp lệ.")
            return value

        if not isinstance(payload, dict):
            raise ValueError("Yêu cầu lập lịch chưa đầy đủ.")
        region, mode = payload.get("region"), payload.get("mode", "car")
        origin, lodging = payload.get("origin", ""), payload.get("lodging_type", "")
        if (not all(isinstance(value, str) for value in (region, mode, origin, lodging))
                or region not in REGIONS or mode not in MODES or lodging not in {"", *LODGING_TYPES}):
            raise ValueError("Chọn điểm đến, phương tiện và loại chỗ ở hợp lệ.")
        if origin and origin not in STARTS[region]:
            raise ValueError("Điểm xuất phát phải thuộc vùng đang chọn.")
        try:
            departure = date.fromisoformat(payload.get("departure", ""))
            departure + timedelta(days=MAX_DAYS)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Ngày đi không hợp lệ.") from None
        if departure < today:
            raise ValueError("Ngày đi phải từ hôm nay trở đi.")
        interests = payload.get("interests", [])
        if not isinstance(interests, list) or any(not isinstance(key, str) or key not in INTERESTS for key in interests):
            raise ValueError("Chọn sở thích trong danh sách.")
        reserves = payload.get("allowances", {})
        if not isinstance(reserves, dict) or set(reserves) - CATEGORIES.keys():
            raise ValueError("Các khoản dự trù không hợp lệ.")
        amount = integer(payload.get("budget"), 1, 10**10, "Tổng ngân sách")
        return cls(region, departure, integer(payload.get("days"), 1, MAX_DAYS, "Số ngày"),
                   integer(payload.get("people"), 1, 99, "Số khách"), amount, mode, origin,
                   tuple(dict.fromkeys(interests)), lodging,
                   {key: integer(value, 0, amount, "Khoản dự trù") for key, value in reserves.items()})


def _fold(text):
    return "".join(char for char in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
                   if not unicodedata.combining(char))


def _hours(raw):
    spans = []
    for a, b, c, d in HOURS.findall(raw or ""):
        start, end = int(a) * 60 + int(b), int(c) * 60 + int(d)
        if start < end <= 1440:
            spans.append((start, end))
    return sorted(spans)


def _clock(minute):
    return f"{minute // 60:02d}:{minute % 60:02d}" if minute is not None else None


def _fits_window(earliest, duration, windows):
    for opens, closes in windows or [(DAY_START, DAY_END)]:
        start = max(earliest, opens)
        if start + duration <= min(DAY_END, closes):
            return start
    return None


def _valid_fee(fee, day):
    try:
        begin = date.fromisoformat(fee["valid_from"]) if fee.get("valid_from") else None
        end = date.fromisoformat(fee["valid_to"]) if fee.get("valid_to") else None
    except ValueError:
        return False
    return (begin is None or begin <= day) and (end is None or day <= end)


def _fee_key(fee, preferred):
    return (fee.get("fee_type") != "official_fee",
            fee["cost_id"] != preferred, fee["price_max_vnd"], fee["cost_id"])


def _place_fee(place, fees, day, selected_groups, selected_areas):
    related = fees.get(place["place_id"], [])
    valid = [fee for fee in related if _valid_fee(fee, day)]
    covered = next((fee for fee in valid if (fee.get("area_id") or place.get("area_id")) in selected_areas), None)
    if covered:
        return {"amount": 0, "source": covered["source"], "included": True,
                "area": covered.get("area_id") or place["area_id"], "group": ""}
    # Rows which specify alternatives are candidates only once per group.
    available = [fee for fee in valid if fee.get("alternative_group") not in selected_groups
                 or fee["cost_id"] == selected_groups[fee.get("alternative_group")]]
    if valid and not available:
        return {"blocked": True}
    row = min(available, key=lambda fee: _fee_key(fee, place.get("ticket_cost_id")), default=None)
    if row:
        area = row.get("area_id") or place.get("area_id") or row["cost_id"]
        group = row.get("alternative_group") or ""
        if area in selected_areas:
            return {"amount": 0, "source": row["source"], "included": True, "area": area, "group": group}
        return {"amount": row["price_max_vnd"], "source": row["source"], "area": area, "group": group,
                "cost_id": row["cost_id"], "opening_hours": row.get("opening_hours", "")}
    area = place.get("area_id") or place["place_id"]
    if area in selected_areas:
        return {"amount": 0, "source": place["source"], "included": True, "area": area, "group": ""}
    if not related and not place.get("ticket_cost_id") and place["ticket_vnd"] is not None and place["source"]:
        return {"amount": place["ticket_vnd"], "source": place["source"], "area": area, "group": ""}
    return None


def _route_finder(catalog, region, mode):
    graph = {}
    for row in catalog.routes:
        if row["region"] != region or row["mode"] != mode:
            continue
        graph.setdefault(row["from_place_id"], []).append(row)

    @lru_cache(maxsize=2048)
    def route(origin, target):
        if origin == target:
            return {"minutes": 0, "distance": 0, "source": "", "stops": ()}
        queue = [(0, origin, 0, (), ())]
        seen = set()
        while queue:
            minute, current, km, trail, sources = heappop(queue)
            if current in seen:
                continue
            if current == target:
                return {"minutes": ceil(minute), "distance": round(km, 1), "stops": trail,
                        "source": "; ".join(dict.fromkeys(sources))}
            seen.add(current)
            for edge in graph.get(current, ()):
                destination = edge["to_place_id"]
                if destination not in seen:
                    heappush(queue, (minute + edge["duration_min"], destination, km + edge["distance_km"],
                                    (*trail, destination), (*sources, edge["source"])))
        return None

    return route


def _rainy(weather):
    probability = weather.get("rain_probability")
    return weather.get("source") == "forecast" and isinstance(probability, (int, float)) and probability >= RAIN_THRESHOLD * 100


def _indoors(place):
    return place["setting"] == "indoor" and not place["rain_sensitive"]


def _candidates(catalog, region):
    fees = {}
    for row in catalog.costs:
        if (row["region"] == region and row["category"] in {"ticket", "activity"}
                and row["unit"] in {"per_person", "per_activity"} and row["basis"] == "person" and row["place_id"]):
            fees.setdefault(row["place_id"], []).append(row)
    points = {
        row["place_id"]: row for row in catalog.places
        if row["region"] == region and row["lat"] is not None
    }
    route_ids = {row[key] for row in catalog.routes if row["region"] == region for key in ("from_place_id", "to_place_id")}
    eligible = [
        point for point in points.values()
        if (point["place_id"] in fees or point["ticket_vnd"] is not None or point["place_id"] in route_ids
            or point["setting"] is not None)
        and point["category"] != "food" and "san bay" not in _fold(point["name"])
        and point["place_id"] != "H01"
    ]
    return points, eligible, fees


def _schedule(request, catalog, points, eligible, fees, weathers, *, ticket_budget, indoor_selector=None):
    route = _route_finder(catalog, request.region, request.mode)
    anchor = request.origin or next((key for key in STARTS[request.region] if key in points), "")
    visited, paid_areas, picked_groups = set(), set(), {}
    ticket_remaining = ticket_budget
    result = []
    for offset, weather in enumerate(weathers):
        when = request.departure + timedelta(days=offset)
        current, earliest = anchor, DAY_START
        items = []
        rainy = _rainy(weather)
        ai_selection = None
        for _ in range(STOPS_PER_DAY):
            choices = []
            for place in eligible:
                ident = place["place_id"]
                if ident in visited or (place["best_months"] and when.month not in place["best_months"]):
                    continue
                if rainy and place["rain_sensitive"]:
                    continue
                fee = _place_fee(place, fees, when, picked_groups, paid_areas)
                if fee and fee.get("blocked"):
                    continue
                amount = fee["amount"] * request.people if fee else None
                if amount is not None and amount > ticket_remaining:
                    continue
                leg = route(current, ident) if current else None
                if leg is None and items:
                    continue
                duration = ceil(place["duration_hours"] * 60)
                hours_text = place.get("opening_hours") or (fee or {}).get("opening_hours") or ""
                windows = _hours(hours_text)
                candidate_start = _fits_window(earliest + (leg["minutes"] if leg else 0), duration, windows)
                if candidate_start is None:
                    continue
                # When rain is forecast, a confirmed indoor option takes priority.
                # Otherwise prefer a directed leg, then the trip interests and known opening hour data.
                preference = place["category"] in request.interests
                rank = (leg is None, rainy and not _indoors(place), not preference,
                        amount is None, not bool(windows), leg["minutes"] if leg else 0,
                        amount if amount is not None else 0, ident)
                choices.append((rank, place, fee, amount, leg, candidate_start, duration, bool(windows)))
            if not choices:
                break
            selected = min(choices, key=lambda choice: choice[0])
            if rainy and not items and indoor_selector:
                verified = sorted(
                    (choice for choice in choices if _indoors(choice[1]) and choice[3] is not None and choice[4]),
                    key=lambda choice: choice[0],
                )[:3]
                if len(verified) > 1:
                    by_id = {choice[1]["place_id"]: choice for choice in verified}
                    reply = indoor_selector([{"id": ident, "value": choice[4]["minutes"]} for ident, choice in by_id.items()])
                    if reply and reply["text"] in by_id and reply["tokens_in"] > 0 and reply["tokens_out"] > 0:
                        selected = by_id[reply["text"]]
                        ai_selection = {key: reply[key] for key in ("model", "tokens_in", "tokens_out")}
                        ai_selection.update(place_id=reply["text"], candidate_count=len(by_id))
            _, place, fee, amount, leg, start, duration, has_hours = selected
            visited.add(place["place_id"])
            if fee is not None and amount is not None:
                paid_areas.add(fee["area"])
                if fee.get("group") and fee.get("cost_id"):
                    picked_groups[fee["group"]] = fee["cost_id"]
                ticket_remaining -= amount
            items.append({
                "id": place["place_id"], "name": place["name"], "lat": place["lat"], "lon": place["lon"],
                "category": place["category"], "indoor": _indoors(place), "duration": duration,
                "duration_estimate": place["duration_is_estimate"], "arrival": _clock(start if leg else None),
                "has_hours": has_hours, "fee": amount, "fee_source": fee["source"] if fee else "",
                "included": bool(fee and fee.get("included")), "source": place["source"], "leg": leg,
                "from_name": points[current]["name"] if current in points else "Điểm xuất phát",
            })
            earliest = start + duration
            current = place["place_id"]
            if leg is None:
                break  # Do not infer a scheduled arrival after an unknown travel interval.
        result.append({"date": when.isoformat(), "items": items, "weather": weather,
                       "ai_selection": ai_selection,
                       "origin": points.get(anchor, {}).get("name", ""),
                       "return_missing": bool(items and offset + 1 < request.days and route(current, anchor) is None),
                       "return_leg": route(current, anchor) if items and offset + 1 < request.days else None})
    return result


def _weather_requests(schedule, request):
    queries = []
    for index, day in enumerate(schedule):
        items = day["items"]
        coords = [(item["lat"], item["lon"]) for item in items]
        lat, lon = (tuple(sum(values) / len(coords) for values in zip(*coords)) if coords else REGIONS[request.region])
        queries.append((lat, lon, request.departure + timedelta(days=index)))
    return queries


def _room_estimate(row, people):
    unit = row["price_unit"]
    published = row.get("published_unit", "")
    explicit = (unit == "per_room_night" and bool(row.get("published_capacity")) and not row["price_unit_is_estimate"]
                or unit == "per_person_night" and published in {"per_person_night", "bed_night", "giường", "giuong"})
    if not explicit:
        return None
    is_room = unit == "per_room_night"
    capacity = row["published_capacity"] if is_room else 1
    count = ceil(people / capacity)
    return {"low": row["price_min_vnd"] * count, "high": row["price_max_vnd"] * count, "rooms": count,
            "unit": "phòng" if is_room else "suất/giường", "capacity": capacity}


def _overnight(catalog, request, end, cap):
    ranking = []
    for row in catalog.lodging:
        if row["region"] != request.region or (request.lodging_type and request.lodging_type != row["type"]):
            continue
        area_match = False
        if end is not None:
            name = _fold(end["name"])
            area_match = any(len(area.strip()) > 4 and _fold(area.strip()) in name
                             for area in re.split(r"[–—/]", row["area"]))
        distance = (round(haversine(row["lat"], row["lon"], end["lat"], end["lon"]), 1)
                    if end is not None and row["lat"] is not None and row["lon"] is not None else None)
        if not area_match and (distance is None or distance > NEARBY_LODGING_KM):
            continue
        estimated = _room_estimate(row, request.people)
        within = estimated is not None and estimated["high"] <= cap
        if (estimated is None and row["price_min_vnd"] > cap) or (estimated is not None and not within):
            continue
        card = {
            "id": row["lodging_id"], "name": row["name"], "type": row["type"], "area": row["area"],
            "distance": distance, "computed": estimated, "reference_from": row["price_min_vnd"],
            "source": row["source"], "source_date": row["source_date"], "fits": within,
        }
        # Prefer prices with a verified unit that fit the nightly cap; then favor nearby properties.
        rank = (not within, 0 if area_match else distance if distance is not None else 9999,
                estimated["high"] if estimated else row["price_min_vnd"], card["id"])
        ranking.append((rank, card))
    cards, used = [], set()
    for _, card in sorted(ranking, key=lambda pair: pair[0]):
        if card["id"] not in used:
            cards.append(card)
            used.add(card["id"])
            if len(cards) == 3:
                break
    return cards, next((card for card in cards if card["fits"]), None)


def _base_charges(request, catalog):
    records = [row for row in catalog.costs if row["region"] == request.region]
    charges = []
    meal = min((row for row in records if row["category"] == "food" and row["unit"] == "per_meal"),
               key=lambda row: row["price_max_vnd"], default=None)
    if meal:
        charges.append(("food", f"Món tham khảo × {MEALS_PER_DAY} bữa mỗi người/ngày",
                        meal["price_max_vnd"] * request.people * request.days * MEALS_PER_DAY, meal["source"]))
    if request.mode == "motorbike":
        rental = min((row for row in records if row["category"] == "bike_rental" and row["unit"] == "per_day"),
                     key=lambda row: row["price_max_vnd"], default=None)
        if rental:
            charges.append(("transport", "Thuê xe theo mẫu, chưa gồm xăng",
                            rental["price_max_vnd"] * ceil(request.people / PEOPLE_PER_MOTORBIKE) * request.days,
                            rental["source"]))
    return charges


def _charge_book(request, catalog, schedule, base_charges):
    buckets = {category: {"amount": 0, "entries": [], "missing": [], "allowance": 0} for category in CATEGORIES}

    def add(category, name, amount, source):
        buckets[category]["amount"] += amount
        buckets[category]["entries"].append({"name": name, "amount": amount, "source": source})

    for charge in base_charges:
        add(*charge)

    for day in schedule:
        for item in day["items"]:
            if item["fee"] is None:
                buckets["ticket"]["missing"].append("Vé " + item["name"])
            elif not item["included"]:
                add("ticket", item["name"], item["fee"], item["fee_source"])
            if item["leg"] is None:
                buckets["transport"]["missing"].append(item["from_name"] + " → " + item["name"])
        if day["return_missing"]:
            buckets["transport"]["missing"].append("Chặng về " + day["origin"])

    bounds = next((row for row in catalog.lodging_bands
                   if row["region_id"] == request.region and row["zone"] == "ALL"
                   and row["accommodation_type"] == (request.lodging_type or "hotel")), None)
    if not buckets["food"]["entries"]:
        buckets["food"]["missing"].append("Chi phí ăn uống cho cả nhóm")
    else:
        buckets["food"]["missing"].append("Phần ăn uống ngoài định mức món tham khảo")
    buckets["transport"]["missing"].append("Chi phí thực tế theo phương tiện và tuyến")
    remaining = max(0, request.budget - sum(row["amount"] for row in buckets.values()) - sum(request.allowances.values()))
    overnight_count = max(0, len(schedule) - 1)
    for day in schedule[:-1]:
        end = day["items"][-1] if day["items"] else None
        candidates, selected = _overnight(catalog, request, end, remaining // overnight_count)
        day["lodgings"] = candidates
        day["lodging_reference"] = ({"median": int(bounds["median_listing_from_vnd"]), "date": bounds["checked_at"]}
                                    if bounds and bounds["median_listing_from_vnd"].isdigit() and not selected else None)
        if selected:
            selected["selected"] = True
            add("lodging", selected["name"], selected["computed"]["high"], selected["source"])
        else:
            buckets["lodging"]["missing"].append("Lưu trú đêm " + day["date"])

    for category, bucket in buckets.items():
        if bucket["missing"] and request.allowances.get(category, 0):
            bucket["allowance"] = request.allowances[category]
    return buckets


def build_trip(request, catalog, *, weather_provider=trip_weather, indoor_selector=None):
    points, eligible, fees = _candidates(catalog, request.region)
    base_charges = _base_charges(request, catalog)
    ticket_budget = max(0, request.budget - sum(charge[2] for charge in base_charges) - sum(request.allowances.values()))
    dry = _schedule(request, catalog, points, eligible, fees, [{} for _ in range(request.days)], ticket_budget=ticket_budget)
    weather = weather_provider(_weather_requests(dry, request))
    schedule = _schedule(request, catalog, points, eligible, fees, weather,
                         ticket_budget=ticket_budget, indoor_selector=indoor_selector)
    for previous, day in zip(dry, schedule):
        before = {item["id"]: item for item in previous["items"]}
        after = {item["id"]: item for item in day["items"]}
        removed = [item["name"] for ident, item in before.items() if ident not in after and not item["indoor"]]
        added = [item["name"] for ident, item in after.items() if ident not in before and item["indoor"]]
        if _rainy(day["weather"]) and removed and added:
            day["reason"] = f"Ưu tiên trong nhà vì dự báo mưa. Đổi {removed[0]} sang {added[0]}."
        elif _rainy(day["weather"]):
            day["reason"] = "Dự báo mưa. Ưu tiên điểm trong nhà và kiểm tra điều kiện trước khi đi."
        elif day["weather"].get("source") == "history":
            backup = next((row["name"] for row in eligible if _indoors(row) and row["place_id"] not in after), None)
            day["reason"] = "Phương án dự phòng nếu mưa: " + backup + "." if backup else ""
        else:
            day["reason"] = ""
        start = request.origin or next((key for key in STARTS[request.region] if key in points), "")
        day["origin_point"] = ({"lat": points[start]["lat"], "lon": points[start]["lon"]} if start in points else None)

    costs = _charge_book(request, catalog, schedule, base_charges)
    total = sum(row["amount"] for row in costs.values())
    reserved = sum(row["allowance"] for row in costs.values())
    remaining = request.budget - total - reserved
    complete = all(not row["missing"] or row["allowance"] for row in costs.values())
    return {"region": request.region, "name": REGION_NAMES[request.region], "days": schedule, "people": request.people,
            "budget": request.budget, "total_known": total, "total_reserved": reserved, "remaining": remaining,
            "budget_status": "over" if remaining < 0 else "within" if complete else "partial", "costs": costs}
