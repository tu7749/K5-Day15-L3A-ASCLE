"""Ánh xạ chỉ đọc CSV sang schema của Đi Vừa Túi, kèm dấu vết nguồn."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
import unicodedata

import config as cfg

# Mỗi phần tử liệt kê cột chuẩn và tên cột gốc duy nhất. Cột chuẩn có ưu tiên.
FIELD_MAP = {
    "places": {
        "place_id": "id", "region": "thanh_pho", "name": "ten", "lat": "lat", "lon": "lon",
        "setting": "loai", "duration_hours": "thoi_luong_phut", "ticket_vnd": "ve_vnd",
        "best_months": "mua_dep", "category": "loai_osm", "source": "nguon_toa_do",
        "source_date": "ngay_kiem", "ticket_cost_id": "ve_cost_id",
        "opening_hours": "gio_mo_cua", "area_id": "ma_khu",
    },
    "costs": {
        "cost_id": "id", "region": "thanh_pho", "category": "hang_muc", "item": "mo_ta",
        "unit": "don_vi", "price_min_vnd": "gia_min_vnd", "price_max_vnd": "gia_max_vnd",
        "notes": "ghi_chu", "source": "nguon", "source_date": "ngay_kiem", "place_id": "place_id",
        "opening_hours": "gio_mo_cua", "fee_type": "loai_gia", "alternative_group": "nhom_thay_the",
        "valid_from": "ap_dung_tu", "valid_to": "ap_dung_den", "area_id": "ma_khu",
    },
    "routes": {
        "from_place_id": "tu_id", "to_place_id": "den_id", "distance_km": "km",
        "duration_min": "phut_max", "mode": "loai_so", "note": "ghi_chu",
        "region": "thanh_pho", "source": "nguon", "source_date": "ngay_kiem",
    },
    "accommodations": {
        "lodging_id": "accommodation_id", "region": "region_id", "name": "name",
        "type": "accommodation_type", "area": "zone", "lat": "latitude", "lon": "longitude",
        "price_min_vnd": "reference_from_vnd", "price_max_vnd": "reference_to_vnd",
        "price_unit": "reference_price_unit", "source": "price_source_url", "source_date": "checked_at",
    },
    "accommodation_prices": {
        "price_id": "price_id", "lodging_id": "accommodation_id", "price_min_vnd": "price_from_vnd",
        "price_max_vnd": "price_to_vnd", "price_unit": "rate_unit",
        "capacity_persons": "adults_per_unit", "source": "price_source_url", "source_date": "checked_at",
        "rate_kind": "rate_kind",
    },
}
CORE_COLUMNS = {
    "places": ("place_id", "region", "name", "lat", "lon", "setting", "duration_hours", "ticket_vnd", "best_months", "category", "source", "source_date"),
    "costs": ("cost_id", "region", "category", "item", "unit", "price_min_vnd", "price_max_vnd", "notes", "source", "source_date"),
    "routes": ("from_place_id", "to_place_id", "distance_km", "duration_min", "mode", "note"),
    "accommodations": tuple(FIELD_MAP["accommodations"]),
    "accommodation_prices": tuple(field for field in FIELD_MAP["accommodation_prices"] if field != "rate_kind"),
    "lodging": ("lodging_id", "region", "name", "type", "area", "lat", "lon", "price_min_vnd",
                "price_max_vnd", "price_unit", "capacity_persons", "rating", "tier", "source", "source_date"),
    "duration_overrides": ("place_id", "duration_hours", "source"),
    "accommodation_budget_bands": ("region_id", "zone", "accommodation_type", "rate_unit", "median_listing_from_vnd", "checked_at"),
}
COST_CATEGORIES = {
    "an_uong": "food", "thue_xe_may": "bike_rental", "thue_o_to": "car_rental", "xang": "fuel",
    "xe_khach": "intercity_transport", "may_bay": "intercity_transport", "tau_hoa": "intercity_transport",
    "ve": "ticket", "thuyen": "activity", "cho_o": "lodging_fallback",
}
COST_UNITS = {
    "mon": ("per_meal", "person"), "xe_ngay": ("per_day", "vehicle"),
    "xe_chuyen": ("per_trip", "vehicle"), "nguoi_chuyen": ("per_trip", "person"),
    "nguoi_luot": ("per_person", "person"), "nguoi_khu_hoi": ("per_person", "round_trip"),
    "nguoi_chieu": ("per_person", "one_way"), "phong_dem": ("per_day", "room"),
    "giuong_dem": ("per_day", "bed"), "thuyen_luot": ("per_activity", "vehicle"),
}
# Phân loại có căn cứ từ thẻ OSM. Ô/nhãn chưa biết vẫn là None; đặt tên nhóm other chỉ để tra mặc định thời lượng.
OSM_CATEGORY = {
    "tourism/viewpoint": "viewpoint", "man_made/tower": "viewpoint",
    "tourism/museum": "culture", "historic": "culture", "amenity/place_of_worship": "culture",
    "tourism/attraction": "activity", "tourism/theme_park": "activity",
    "natural": "nature", "boundary/protected_area": "nature",
    "amenity/marketplace": "market", "amenity/restaurant": "food", "amenity/cafe": "food",
    "man_made/bridge": "viewpoint",
}
OSM_OUTDOOR = frozenset({
    "man_made/bridge", "man_made/tower", "natural/wood", "natural/beach", "place/village",
})
PLACE_SETTINGS = {"trong_nha": "indoor", "ngoai_troi": "outdoor", "indoor": "indoor", "outdoor": "outdoor"}
ROOM_UNITS = {
    "room_night": "per_room_night", "phòng": "per_room_night", "phong": "per_room_night",
    "per_room_night": "per_room_night", "bed_night": "per_person_night", "giường": "per_person_night",
    "giuong": "per_person_night", "per_person_night": "per_person_night",
}
LODGING_TIERS = ("budget", "mid", "comfort")
# CSV phân loại hostel riêng. Schema chuẩn không có hostel, nên báo và giữ ngoài bộ tính giá.
LODGING_TYPES = frozenset({"hotel", "guesthouse", "homestay"})


@dataclass
class Catalog:
    places: list[dict] = field(default_factory=list)
    costs: list[dict] = field(default_factory=list)
    routes: list[dict] = field(default_factory=list)
    lodging: list[dict] = field(default_factory=list)
    lodging_bands: list[dict] = field(default_factory=list)
    source: str = "local"
    audit: Counter = field(default_factory=Counter)


def _mapped(row, name):
    return {key: row.get(key, row.get(old, "")).strip() for key, old in FIELD_MAP.get(name, {}).items()}


def _integer(value):
    return int(value) if value and value.isascii() and value.isdecimal() else None


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _marks(low, high):
    lower, upper = _integer(low), _integer(high)
    return (lower, upper) if None not in (lower, upper) and lower <= upper else None


def _coordinates(lat, lon):
    lat, lon = _number(lat), _number(lon)
    return (lat, lon) if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 else (None, None)


def _date_valid(value):
    try:
        return datetime.fromisoformat(value).date().isoformat() == value
    except ValueError:
        return False


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.casefold()) if not unicodedata.combining(c))


def _tier_lodging(entries):
    for region in cfg.REGIONS:
        complete = sorted(
            (row for row in entries if row["region"] == region and row["room_price_min_vnd"] is not None),
            key=lambda row: (row["room_price_min_vnd"] + row["room_price_max_vnd"], row["lodging_id"], row["price_id"]),
        )
        # Đếm theo cơ sở, không để khách sạn nhiều giá chi phối tam phân vị.
        cheapest = {}
        for row in complete:
            cheapest.setdefault(row["lodging_id"], row["room_price_min_vnd"] + row["room_price_max_vnd"])
        values = sorted(cheapest.values())
        cutoffs = [values[(len(values) - 1) * part // 3] for part in (1, 2)] if values else []
        for row in complete:
            if not row["tier"]:
                value = cheapest[row["lodging_id"]]
                row["tier"] = "budget" if len(values) < cfg.TIER_MIN_SAMPLE else LODGING_TIERS[
                    sum(value > cutoff for cutoff in cutoffs)
                ]
                row["tier_is_estimate"] = True


def _lodging(info, price, audit):
    region = info["region"]
    kind = info["type"]
    key = f"lodging/{region}"
    if region not in cfg.REGIONS or kind not in LODGING_TYPES:
        audit[f"{key}/outside_or_unsupported_type"] += 1
        return None
    lower = _integer(price["price_min_vnd"])
    upper = _integer(price["price_max_vnd"])
    is_point = lower is not None and not price["price_max_vnd"]
    if is_point:
        upper = lower
    if lower is None or upper is None or lower > upper or not price["source"] or not _date_valid(price["source_date"]):
        audit[f"{key}/missing_or_invalid_price_or_source"] += 1
        return None

    raw_unit = price["price_unit"].casefold()
    unit = ROOM_UNITS.get(raw_unit, "unit_unknown")
    # Một dòng quảng cáo giá dorm có thể tính theo giường dù cơ sở được xếp là khách sạn.
    is_unspecified_dorm = raw_unit in cfg.AMBIGUOUS_NIGHT_UNITS and price.get("rate_kind") == "operator_dorm_from"
    assumed_unit = raw_unit in cfg.AMBIGUOUS_NIGHT_UNITS and kind in cfg.ASSUMED_ROOM_TYPES and not is_unspecified_dorm
    if assumed_unit:
        unit = "per_room_night"
    capacity = _integer(price.get("capacity_persons", "")) or None
    bed_equivalent = raw_unit in {"bed_night", "giường", "giuong"}
    assumed_capacity = capacity is None and unit != "unit_unknown" and not bed_equivalent
    if assumed_capacity:
        capacity = cfg.ROOM_CAPACITY_DEFAULT
    if bed_equivalent:
        capacity = cfg.ONE_BED_PERSONS
    audit[f"{key}/point_price"] += is_point
    audit[f"{key}/assumed_unit"] += assumed_unit
    audit[f"{key}/assumed_capacity"] += assumed_capacity
    audit[f"{key}/unknown_unit"] += unit == "unit_unknown"
    audit[f"{key}/unspecified_dorm_unit"] += is_unspecified_dorm
    audit[f"{key}/confidence_capped"] += is_point or assumed_unit or assumed_capacity or unit == "unit_unknown"

    lat, lon = _coordinates(info["lat"], info["lon"])
    room_multiplier = capacity if unit == "per_person_night" else 1 if unit == "per_room_night" else None
    return {
        "lodging_id": info["lodging_id"], "price_id": price.get("price_id") or info["lodging_id"],
        "region": region, "name": info["name"], "type": kind, "area": info["area"], "lat": lat, "lon": lon,
        "price_min_vnd": lower, "price_max_vnd": upper, "price_unit": unit,
        "capacity_persons": capacity, "rating": _number(info.get("rating")),
        "published_capacity": _integer(price.get("capacity_persons", "")), "published_unit": raw_unit,
        "tier": info.get("tier") or None, "tier_is_estimate": False,
        "source": price["source"], "source_date": price["source_date"], "price_is_point": is_point,
        "price_unit_is_estimate": assumed_unit or bed_equivalent,
        "capacity_is_estimate": assumed_capacity or bed_equivalent,
        "room_price_min_vnd": lower * room_multiplier if room_multiplier is not None else None,
        "room_price_max_vnd": upper * room_multiplier if room_multiplier is not None else None,
    }


def adapt(tables: dict[str, list[dict]], source: str) -> Catalog:
    catalog = Catalog(source=source)
    overrides = {}
    for raw in tables.get("duration_overrides", []):
        value = _number(raw["duration_hours"])
        if not raw["place_id"] or not raw["source"] or value is None or value <= 0 or raw["place_id"] in overrides:
            raise ValueError(f"duration_overrides.csv có bản ghi sai hoặc trùng mã: {raw['place_id']}")
        overrides[raw["place_id"]] = (value, raw["source"])

    for raw in tables["places"]:
        row = _mapped(raw, "places")
        if row["region"] not in cfg.REGIONS:
            catalog.audit[f"outside/places/{row['region'] or '(trống)'}"] += 1
            continue
        lat, lon = _coordinates(row["lat"], row["lon"])
        category = row["category"]
        if category not in cfg.DURATION_HOURS:
            category = OSM_CATEGORY.get(category, OSM_CATEGORY.get(category.split("/")[0], "other"))
        duration = _number(row["duration_hours"])
        if duration is not None and "duration_hours" not in raw:
            duration /= 60
        override = overrides.get(row["place_id"])
        duration_is_estimate = override is None and (duration is None or duration <= 0)
        duration, duration_source = override or (
            cfg.DURATION_HOURS[category] if duration_is_estimate else duration,
            "config.py:DURATION_HOURS" if duration_is_estimate else row["source"],
        )
        months = tuple(int(item.strip()) for item in row["best_months"].split(";") if item.strip().isdecimal())
        if row["best_months"] and not months:
            catalog.audit[f"places/{row['region']}/unparsed_months"] += 1
        setting = PLACE_SETTINGS.get(row["setting"])
        if setting is None and raw.get("loai_osm") in OSM_OUTDOOR:
            setting = "outdoor"
        catalog.places.append({
            **row, "lat": lat, "lon": lon, "setting": setting,
            "setting_is_estimate": not row["setting"] and setting is not None,
            "duration_hours": duration, "duration_is_estimate": duration_is_estimate,
            "duration_source": duration_source,
            "duration_source_date": None if override else cfg.ASSUMPTION_SOURCE_DATE if duration_is_estimate else row["source_date"],
            "ticket_vnd": _integer(row["ticket_vnd"]),
            "best_months": months, "category": category,
            "category_is_estimate": not row["category"] or category != row["category"],
            "rain_sensitive": raw.get("loai_osm") == "natural/cave_entrance",
        })

    for raw in tables["costs"]:
        row = _mapped(raw, "costs")
        if row["region"] not in cfg.REGIONS:
            catalog.audit[f"outside/costs/{row['region'] or '(trống)'}"] += 1
            continue
        prices = _marks(row["price_min_vnd"], row["price_max_vnd"])
        unit, basis = COST_UNITS.get(row["unit"], (row["unit"], "person"))
        if not prices or unit not in {"per_meal", "per_day", "per_trip", "per_person", "per_activity"} or not row["source"]:
            catalog.audit[f"costs/{row['region']}/missing_price_or_unsupported_unit"] += 1
            continue
        catalog.costs.append({
            **row, "category": "ticket" if row["category"] == "official_fee" else
            COST_CATEGORIES.get(row["category"], row["category"] if "category" in raw else "other"),
            "fee_type": row["fee_type"] or ("official_fee" if row["category"] == "official_fee" else ""),
            "unit": unit, "basis": basis, "price_min_vnd": prices[0], "price_max_vnd": prices[1],
        })

    place_regions = {row["place_id"]: row["region"] for row in catalog.places}
    for raw in tables["routes"]:
        row = _mapped(raw, "routes")
        start, end = row["from_place_id"], row["to_place_id"]
        region = row["region"] or place_regions.get(start, "")
        if row["region"] and row["region"] not in cfg.REGIONS:
            catalog.audit[f"outside/routes/{row['region']}"] += 1
            continue
        mode = {"osrm_oto": "car", "bus": "transit", "xe_buyt": "transit"}.get(row["mode"], row["mode"])
        distance, duration = _number(row["distance_km"]), _number(row["duration_min"])
        if (region not in cfg.REGIONS or place_regions.get(start) != region or place_regions.get(end) != region
                or mode not in {"motorbike", "car", "transit"} or distance is None or duration is None or distance < 0 or duration <= 0):
            catalog.audit[f"routes/{region or '(trống)'}/missing_or_unverified_route"] += 1
            continue
        catalog.routes.append({
            **row, "region": region, "mode": mode, "distance_km": distance, "duration_min": duration,
            "source": row["source"] or "data/routes.csv", "source_date": row["source_date"] or None,
        })

    if "lodging" in tables:
        lodging_inputs = [(row, {**row, "price_id": row["lodging_id"]}) for row in tables["lodging"]]
    else:
        by_id = {}
        for raw in tables.get("accommodations", []):
            row = _mapped(raw, "accommodations")
            key = row["lodging_id"]
            if not key or key in by_id:
                raise ValueError(f"accommodations.csv có mã cơ sở trống hoặc trùng: {key}")
            by_id[key] = row
        details = defaultdict(list)
        for raw in tables.get("accommodation_prices", []):
            row = _mapped(raw, "accommodation_prices")
            if row["lodging_id"] not in by_id:
                catalog.audit["lodging/orphan_price"] += 1
                continue
            details[row["lodging_id"]].append(row)
        lodging_inputs = [(info, price) for ident, info in by_id.items() for price in details.get(ident, [info])]
    for info, price in lodging_inputs:
        if info["region"] not in cfg.REGIONS:
            catalog.audit[f"outside/lodging/{info['region'] or '(trống)'}"] += 1
            continue
        if entry := _lodging(info, price, catalog.audit):
            catalog.lodging.append(entry)
    _tier_lodging(catalog.lodging)
    catalog.lodging_bands = [row for row in tables.get("accommodation_budget_bands", []) if row["region_id"] in cfg.REGIONS]
    return catalog
