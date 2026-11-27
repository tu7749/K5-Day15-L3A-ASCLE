"""Công cụ chỉ đọc cho bản chạy thử ASCLE."""
import csv
from heapq import heappop, heappush
from pathlib import Path

from tracing import tool

DATA = Path(__file__).resolve().parents[1] / "data"
MAX_ROUND_TRIP_MINUTES = 180

# Lịch mẫu CP2 xuất phát và quay lại cùng khu vực mỗi ngày.
DESTINATIONS = {
    "ha_giang": {
        "name": "Hà Giang", "base": "H11",
        "visits": ("H02", "H09", "H11", "H07", "H03"),
        "rain_options": (),
        "lodging": ("C032", "giuong_dem"), "rental": ("C030", "xe_ngay"),
    },
    "da_nang": {
        "name": "Đà Nẵng", "base": "D01",
        "visits": ("D04", "D07", "D01", "D03", "D05"),
        "rain_options": ("D10", "D05"),
        "lodging": ("C121", "phong_dem"), "rental": ("C114", "xe_ngay"),
    },
}


def _rows(filename, destination):
    with (DATA / filename).open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["thanh_pho"] == destination]


def _round_trip_minutes(origin, routes, places):
    adjacency = {place_id: [] for place_id in places}
    for route in routes:
        start, end = route["tu_id"], route["den_id"]
        maximum = route["phut_max"]
        if route["loai_so"] != "osrm_oto" or start not in places or end not in places:
            continue
        if not maximum.isdigit() or int(maximum) <= 0:
            continue
        # Dữ liệu CP2 chỉ có một chiều. Dùng cùng ước tính cho chiều về.
        adjacency[start].append((end, int(maximum)))
        adjacency[end].append((start, int(maximum)))

    times = {}
    queue = [(0, origin)]
    while queue:
        minutes, place_id = heappop(queue)
        if place_id in times:
            continue
        times[place_id] = minutes * 2
        for next_id, segment in adjacency[place_id]:
            if next_id not in times and (minutes + segment) * 2 <= MAX_ROUND_TRIP_MINUTES:
                heappush(queue, (minutes + segment, next_id))
    return times


def _rate(costs, cost_id, unit, category):
    row = costs.get(cost_id)
    if row and row["don_vi"] == unit and row["hang_muc"] == category and row["gia_max_vnd"].isdigit():
        return int(row["gia_max_vnd"])
    return None


@tool
def load_destination(destination: str) -> dict:
    """Đọc bảng giá và cung đường. Input: mã điểm đến. Output: lịch mẫu, điểm thay thế và giá đã đối chiếu. Chỉ đọc CSV local."""
    config = DESTINATIONS[destination]
    places = {row["id"]: row for row in _rows("places.csv", destination)}
    costs = {row["id"]: row for row in _rows("costs.csv", destination)}
    times = _round_trip_minutes(config["base"], _rows("routes.csv", destination), places)

    activities = {}
    for place_id in (*config["visits"], *config["rain_options"]):
        row = places.get(place_id)
        if row is None or place_id not in times:
            continue
        cost_id = row["ve_cost_id"]
        price = _rate(costs, cost_id, "nguoi_luot", "ve")
        if price is None or costs[cost_id]["place_id"] != place_id or str(price) != row["ve_vnd"]:
            continue
        activities[place_id] = {
            "id": place_id, "name": row["ten"], "price_vnd": price, "cost_id": cost_id,
            "round_trip_minutes": times[place_id], "indoor": row["loai"] == "trong_nha",
        }

    lodging_id, lodging_unit = config["lodging"]
    rental_id, rental_unit = config["rental"]
    return {
        "name": config["name"], "base_name": places.get(config["base"], {}).get("ten"),
        "visits": config["visits"], "rain_options": config["rain_options"],
        "activities": activities,
        "lodging_id": lodging_id, "lodging_vnd": _rate(costs, lodging_id, lodging_unit, "cho_o"),
        "rental_id": rental_id, "rental_vnd": _rate(costs, rental_id, rental_unit, "thue_xe_may"),
    }


@tool
def weather_scenario(rain_day: int | None, severe: bool) -> dict:
    """Xác định kịch bản thời tiết. Input: ngày mưa và cờ thời tiết nguy hiểm. Output: trạng thái người dùng nhập hoặc chưa biết. Không gọi API."""
    return {
        "rain_day": rain_day, "severe": severe,
        "source": "kịch bản do người dùng nhập; chưa xác minh" if rain_day else "chưa có dữ liệu",
    }
