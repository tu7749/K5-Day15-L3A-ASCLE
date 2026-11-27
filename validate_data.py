"""Kiểm tra schema chuẩn sau khi ánh xạ; giữ ô chưa biết dưới dạng None."""
from collections import Counter, defaultdict
from datetime import date
from math import isfinite
import sys

import config as cfg
from data_adapter import LODGING_TIERS, LODGING_TYPES

COST_TYPES = frozenset({
    "food", "bike_rental", "car_rental", "fuel", "intercity_transport",
    "ticket", "activity", "lodging_fallback", "other",
})


def _valid_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except (ValueError, TypeError):
        return False


def _valid_range(row):
    low, high = row.get("price_min_vnd"), row.get("price_max_vnd")
    return type(low) is int and type(high) is int and 0 <= low <= high


def _coords(row):
    lat, lon = row.get("lat"), row.get("lon")
    return (lat is None and lon is None) or (
        lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180
    )


def validate_data(data):
    errors = []
    place_lookup = {}
    for row in data.places:
        ident = row["place_id"]
        if (not ident or ident in place_lookup or row["region"] not in cfg.REGIONS or not row["name"]
                or not _coords(row) or row["setting"] not in {None, "indoor", "outdoor"}
                or not isfinite(row["duration_hours"]) or row["duration_hours"] <= 0
                or row["category"] not in cfg.DURATION_HOURS
                or any(month not in range(1, 13) for month in row["best_months"])
                or not _valid_date(row["source_date"])
                or (row["lat"] is not None and not row["source"])):
            errors.append(f"places: dòng {ident or '(trống)'} sai schema chuẩn")
        place_lookup[ident] = row["region"]

    cost_ids = set()
    for row in data.costs:
        ident = row["cost_id"]
        if (not ident or ident in cost_ids or row["region"] not in cfg.REGIONS or row["category"] not in COST_TYPES
                or not row["item"] or not _valid_range(row) or not row["source"] or not _valid_date(row["source_date"])
                or row["unit"] not in {"per_meal", "per_day", "per_trip", "per_person", "per_activity"}):
            errors.append(f"costs: dòng {ident or '(trống)'} sai schema chuẩn")
        cost_ids.add(ident)

    for row in data.routes:
        if (row["region"] not in cfg.REGIONS
                or any(place_lookup.get(row[key]) != row["region"] for key in ("from_place_id", "to_place_id"))
                or row["distance_km"] < 0 or row["duration_min"] <= 0 or row["mode"] not in {"motorbike", "car"}
                or (row["source_date"] is not None and not _valid_date(row["source_date"]))):
            errors.append(f"routes: tuyến {row['from_place_id']} → {row['to_place_id']} sai schema chuẩn")

    price_ids = set()
    for row in data.lodging:
        ident = row["price_id"]
        unit, capacity = row["price_unit"], row["capacity_persons"]
        if (not row["lodging_id"] or not ident or ident in price_ids or row["region"] not in cfg.REGIONS
                or row["type"] not in LODGING_TYPES or not row["name"] or not _coords(row) or not _valid_range(row)
                or (row["rating"] is not None and not 0 <= row["rating"] <= 5)
                or row["tier"] not in {None, *LODGING_TIERS}
                or unit not in {"per_room_night", "per_person_night", "unit_unknown"}
                or (unit != "unit_unknown" and (not capacity or capacity <= 0))
                or not row["source"] or not _valid_date(row["source_date"])):
            errors.append(f"lodging: dòng {ident or '(trống)'} sai schema chuẩn")
        price_ids.add(ident)
    return errors


def counts_by_region(data):
    counts = defaultdict(Counter)
    for name in ("places", "costs", "routes", "lodging"):
        for row in getattr(data, name):
            group = counts[(row["region"], name)]
            group["total"] += 1
            kind = row.get("category", row.get("type", row.get("mode")))
            group[f"type/{kind}"] += 1
            if "lat" in row:
                group["with_coordinates"] += row["lat"] is not None and row["lon"] is not None
    return counts


def main():
    from data_loader import load_data
    try:
        catalog = load_data()
    except (OSError, ValueError) as error:
        print(f"Dữ liệu lỗi: {error}", file=sys.stderr)
        return 1
    for (region, name), counts in sorted(counts_by_region(catalog).items()):
        print(region, name, dict(counts))
    print("Nguồn:", catalog.source)
    print("Số dòng được đánh dấu hoặc bỏ qua:", dict(+catalog.audit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
