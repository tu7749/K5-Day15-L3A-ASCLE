from datetime import date, timedelta
from urllib.error import URLError

import pytest

from data_adapter import Catalog
from data_loader import load_data
from vietdu_planner import Request, _fits_window, _hours, _place_fee, _room_estimate, _route_finder, build_trip
from vietdu_weather import ARCHIVE, FORECAST, _forecast, _history, daily_weather

TODAY = date(2026, 11, 27)


@pytest.fixture(scope="module")
def catalog():
    return load_data(use_s3=False)


def dry(requests):
    return [{"source": "unavailable"} for _ in requests]


def rainy_forecast(requests):
    return [{"source": "forecast", "rain_probability": 85} for _ in requests]


def test_directed_routes_are_not_reversed_or_used_for_the_wrong_mode():
    link = {"region": "ha_giang", "from_place_id": "H1", "to_place_id": "H2", "mode": "car",
            "distance_km": 20, "duration_min": 30, "source": "https://example.com/route"}
    routes = Catalog(routes=[link])
    find = _route_finder(routes, "ha_giang", "car")
    assert find("H1", "H2")["minutes"] == 30
    assert find("H2", "H1") is None
    assert _route_finder(routes, "ha_giang", "motorbike")("H1", "H2") is None


def test_official_validity_alternatives_and_area_admission():
    place = {"place_id": "D1", "ticket_vnd": None, "source": "", "ticket_cost_id": "cheap"}
    own = {"cost_id": "cheap", "price_max_vnd": 40, "source": "https://example.com/reference",
           "alternative_group": "one", "area_id": "zone-a"}
    official = own | {"cost_id": "official", "price_max_vnd": 70, "fee_type": "official_fee",
                      "valid_from": "2026-01-01", "valid_to": "2026-12-31"}
    fees = {"D1": [own, official]}
    assert _place_fee(place, fees, TODAY, {}, set())["amount"] == 70
    assert _place_fee(place, fees, date(2027, 1, 1), {}, set())["amount"] == 40
    assert _place_fee(place, fees, TODAY, {"one": "other"}, set())["blocked"]
    assert _place_fee(place, fees, TODAY, {"one": "other"}, {"zone-a"})["included"]


def test_opening_windows_cover_the_whole_visit():
    hours = _hours("08:00–11:00; 13:00-17:00")
    assert _fits_window(10 * 60, 90, hours) == 13 * 60
    assert _fits_window(16 * 60, 90, hours) is None


def test_estimate_uses_only_confirmed_room_capacity_and_bed_unit():
    room = {"price_unit": "per_room_night", "published_unit": "room_night", "published_capacity": 2,
            "price_unit_is_estimate": False, "price_min_vnd": 200_000, "price_max_vnd": 300_000}
    assert _room_estimate(room, 3)["high"] == 600_000
    assert _room_estimate(room | {"published_capacity": None}, 3) is None
    bed = room | {"price_unit": "per_person_night", "published_unit": "bed_night", "published_capacity": None}
    assert _room_estimate(bed, 3)["high"] == 900_000


def test_da_nang_rain_changes_an_outdoor_stop_and_routes_are_reported(catalog):
    request = Request("da_nang", TODAY, 2, 2, 2_500_000, interests=("nature", "viewpoint"))
    plan = build_trip(request, catalog, weather_provider=rainy_forecast)
    day = plan["days"][0]
    assert "Đổi Ngũ Hành Sơn sang Bảo tàng Điêu khắc Chăm" in day["reason"]
    assert day["items"][0]["arrival"]
    assert day["items"][0]["fee_source"].startswith("https")
    assert day["return_missing"]
    assert plan["budget_status"] == "partial"


@pytest.mark.parametrize(("model_id", "expected"), [("D10", "D10"), ("unknown", "D05")])
def test_rain_model_selects_an_eligible_stop_or_uses_planner_fallback(catalog, model_id, expected):
    request = Request("da_nang", TODAY, 2, 2, 2_500_000, interests=("nature", "viewpoint"))
    shortlists = []

    def select(candidates):
        shortlists.append({row["id"] for row in candidates})
        return {"text": model_id, "model": "test-model", "tokens_in": 20, "tokens_out": 4}

    plan = build_trip(request, catalog, weather_provider=rainy_forecast,
                      indoor_selector=select)
    day = plan["days"][0]
    assert {"D05", "D10"} <= shortlists[0]
    assert day["items"][0]["id"] == expected
    assert (day["ai_selection"] or {}).get("place_id") == (expected if model_id == expected else None)


def test_budget_is_partial_when_unpriced_costs_exist_and_within_after_allowance(catalog):
    request = Request("da_nang", TODAY, 2, 2, 5_000_000, interests=("nature",))
    pending = build_trip(request, catalog, weather_provider=dry)
    assert pending["budget_status"] == "partial"
    reserves = {key: 100_000 for key, cost in pending["costs"].items() if cost["missing"]}
    supplied = Request("da_nang", TODAY, 2, 2, 5_000_000, interests=("nature",), allowances=reserves)
    result = build_trip(supplied, catalog, weather_provider=dry)
    assert result["budget_status"] == "within"
    assert result["total_known"] + result["total_reserved"] + result["remaining"] == result["budget"]


def test_open_meteo_forecast_cache_and_outage(monkeypatch):
    _forecast.cache_clear()
    calls = []

    def response(endpoint, parameters):
        assert endpoint == FORECAST
        calls.append(parameters)
        return {"time": [TODAY.isoformat()], "temperature_2m_min": [22], "temperature_2m_max": [26],
                "precipitation_sum": [12], "precipitation_probability_max": [75], "weather_code": [61]}

    monkeypatch.setattr("vietdu_weather._get", response)
    forecast = daily_weather(22.801, 104.983, TODAY, today=TODAY)
    assert forecast["rain_probability"] == 75 and forecast["rain_mm"] == 12
    assert daily_weather(22.802, 104.984, TODAY, today=TODAY) == forecast
    assert len(calls) == 1

    def offline(*_):
        raise URLError("offline")

    monkeypatch.setattr("vietdu_weather._get", offline)
    _forecast.cache_clear()
    unavailable = daily_weather(22.80, 104.98, TODAY, today=TODAY)
    assert unavailable == {"source": "unavailable"}


def test_open_meteo_archive_uses_five_complete_years(monkeypatch):
    _history.cache_clear()

    def historical(endpoint, parameters):
        assert endpoint == ARCHIVE
        assert parameters["models"] == "era5"
        assert parameters["start_date"] == "2021-01-01" and parameters["end_date"] == "2025-12-31"
        dates = [date(year, 2, 1) + timedelta(days=index)
                 for year in range(2021, 2026) for index in range(29 if year == 2024 else 28)]
        return {"time": [day.isoformat() for day in dates],
                "precipitation_sum": [1 if day.day == 1 else 0.99 for day in dates]}

    monkeypatch.setattr("vietdu_weather._get", historical)
    result = daily_weather(16.04, 108.20, date(2027, 2, 1), today=TODAY)
    assert result["source"] == "history"
    assert (result["reference_start"], result["reference_end"], result["wet_days"], result["total_days"]) == (2021, 2025, 5, 141)


def test_invalid_group_request_is_rejected():
    with pytest.raises(ValueError, match="Tổng ngân sách"):
        Request.parse({"region": "ha_giang", "departure": "2026-11-27", "days": 3, "people": 2, "budget": 0}, TODAY)
