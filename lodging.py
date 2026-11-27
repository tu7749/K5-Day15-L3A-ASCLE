"""Xếp hạng lưu trú, giữ nguyên khoảng và đơn vị nguồn."""
from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt

import config as cfg
from budget import estimate_band
from data_adapter import LODGING_TIERS


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * cfg.EARTH_RADIUS_KM * asin(sqrt(min(1, a)))


def lodging_confidence(row, today):
    age = (today - date.fromisoformat(row["source_date"])).days
    fresh = 0 <= age <= cfg.FRESH_DAYS
    low, high = row["price_min_vnd"], row["price_max_vnd"]
    narrow = high == low or 2 * (high - low) / (high + low) <= cfg.PRICE_WIDTH_MAX
    confidence = ("low", "medium", "high")[int(fresh) + int(narrow)]
    if row["price_unit"] == "unit_unknown":
        return cfg.UNKNOWN_UNIT_CONFIDENCE, fresh
    if confidence == "high" and (row["price_is_point"] or row["price_unit_is_estimate"] or row["capacity_is_estimate"]):
        confidence = cfg.POINT_PRICE_CONFIDENCE_LIMIT
    return confidence, fresh


def quote_lodging(row, nights, people, budget_vnd, places, today):
    confidence, fresh = lodging_confidence(row, today)
    low, high = row["room_price_min_vnd"], row["room_price_max_vnd"]
    rooms = (people + row["capacity_persons"] - 1) // row["capacity_persons"] if low is not None else None
    coordinates = [(p["lat"], p["lon"]) for p in places if p.get("lat") is not None]
    distance = None
    if coordinates and row["lat"] is not None:
        distance = sum(haversine(row["lat"], row["lon"], lat, lon) for lat, lon in coordinates) / len(coordinates)
    source = {"source": row["source"], "source_date": row["source_date"], "confidence": confidence}
    raw_price = estimate_band(row["price_min_vnd"], row["price_max_vnd"], **source)
    nightly_price = estimate_band(low, high, **source) if rooms else None
    total = estimate_band(low * rooms * nights, high * rooms * nights, **source) if rooms else None
    nightly_budget = budget_vnd // (nights * rooms) if nights and rooms else None
    fits = total is not None and total["expected_vnd"] <= budget_vnd
    reason = []
    if total is None:
        reason.append("Chưa rõ đơn vị giá; chưa tính được tổng cho nhóm.")
    elif fits:
        reason.append("Giá ước tính nằm trong ngân sách lưu trú.")
    elif total["min_vnd"] <= budget_vnd:
        reason.append("Có thể vừa nếu chọn phòng giá thấp.")
    else:
        reason.append("Vượt ngân sách lưu trú.")
    if row["price_is_point"]:
        reason.append("Nguồn chỉ có một mức giá tham khảo.")
    if row["price_unit_is_estimate"] or row["capacity_is_estimate"]:
        reason.append("Có giả định về đơn vị hoặc sức chứa.")
    weights = cfg.LODGING_WEIGHTS
    components = {
        "fit": float(fits), "rating": None if row["rating"] is None else row["rating"] / 5,
        "distance": None if distance is None else 1 / (1 + distance), "freshness": float(fresh),
    }
    score = sum(weights[key] * component for key, component in components.items() if component is not None)
    return {
        **row, "is_estimate": True, "nightly_budget_per_room": nightly_budget,
        "price_range": nightly_price or raw_price, "published_price_range": raw_price,
        "expected_price": nightly_price["expected_vnd"] if nightly_price else None,
        "predicted_total": total, "fits_budget": fits,
        "gap_vnd": max(0, total["min_vnd"] - budget_vnd) if total else None,
        "confidence": confidence, "reasons": reason, "rooms": rooms,
        "distance_km": None if distance is None else round(distance, 1), "distance_is_estimate": distance is not None,
        "distance_source": "Tọa độ bảng lưu trú và địa điểm; công thức haversine" if distance is not None else None,
        "distance_source_date": row["source_date"] if distance is not None else None,
        "score": score,
    }


def lodging_options(catalog, region, nights, people, budget_vnd, places=(), *, today=None,
                    lodging_types=(), room_budget_per_night=None, require_upper_bound=False):
    today = today or datetime.now(cfg.TIMEZONE).date()
    rows = [row for row in catalog.lodging if row["region"] == region]
    if not rows:
        for cost in catalog.costs:
            if cost["region"] != region or cost["category"] != "lodging_fallback":
                continue
            if cost["basis"] not in {"room", "bed"}:
                continue
            bed = cost["basis"] == "bed"
            rows.append({
                "lodging_id": cost["cost_id"], "price_id": cost["cost_id"], "region": region,
                "name": cost["item"], "type": None, "area": "", "lat": None, "lon": None, "rating": None,
                "tier": "budget", "tier_is_estimate": True, "price_min_vnd": cost["price_min_vnd"],
                "price_max_vnd": cost["price_max_vnd"], "room_price_min_vnd": cost["price_min_vnd"],
                "room_price_max_vnd": cost["price_max_vnd"], "price_is_point": False,
                "price_unit": "per_person_night" if bed else "per_room_night",
                "price_unit_is_estimate": bed, "capacity_persons": cfg.ONE_BED_PERSONS if bed else cfg.ROOM_CAPACITY_DEFAULT,
                "capacity_is_estimate": True, "source": cost["source"], "source_date": cost["source_date"],
            })
    quotes = [
        quote_lodging(row, nights, people, budget_vnd, places, today)
        for row in rows
        if (not lodging_types or row["type"] in lodging_types)
        and (room_budget_per_night is None or row["price_unit"] == "per_room_night")
    ]
    known = [quote for quote in quotes if quote["predicted_total"] is not None]
    groups = {tier: [] for tier in LODGING_TIERS}

    def price_and_limit(row):
        if room_budget_per_night is not None:
            return row["price_range"], room_budget_per_night
        return row["predicted_total"], budget_vnd

    def fits(row):
        price, limit = price_and_limit(row)
        return price["max_vnd" if require_upper_bound else "min_vnd"] <= limit

    candidates = sorted(known, key=lambda item: (-item["score"], item["predicted_total"]["max_vnd"], item["price_id"]))
    for row in candidates:
        group = groups.get(row["tier"])
        if (group is not None and len(group) < cfg.MAX_LODGING_OPTIONS
                and fits(row)
                and all(option["lodging_id"] != row["lodging_id"] for option in group)):
            group.append(row)
    price_key = "max_vnd" if require_upper_bound else "min_vnd"
    cheapest = min(known, key=lambda row: (price_and_limit(row)[0][price_key], price_and_limit(row)[0]["max_vnd"]), default=None)
    if require_upper_bound:
        if cheapest is not None:
            price, limit = price_and_limit(cheapest)
            cheapest = {**cheapest, "gap_vnd": max(0, price[price_key] - limit)}
        any_fit = any(fits(row) for row in known)
    else:
        any_fit = any(row["fits_budget"] for row in known)
    return {
        "groups": groups, "known": known, "cheapest_outside_allocation": cheapest if not any_fit else None,
        "unpriced": [row for row in quotes if row["predicted_total"] is None],
    }
