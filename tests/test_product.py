import csv
from datetime import date
from itertools import product
from pathlib import Path
from unittest.mock import Mock

import pytest

import config as cfg
import weather_service
from budget import allocate_budget
from data_adapter import _lodging, _tier_lodging, Catalog
from data_loader import load_data
from llm import render_itinerary, validate_output
from lodging import lodging_confidence
from output import format_plan
from planner import TripRequest, build_plan
from validate_data import validate_data

TODAY = date(2026, 11, 27)


@pytest.fixture(scope="module")
def catalog():
    return load_data(use_s3=False)


def make_plan(catalog, **values):
    settings = {"region": "da_nang", "days": 3, "people": 2, "budget_vnd": 3_000_000, "month": 10}
    return build_plan(TripRequest(**(settings | values)), catalog=catalog, today=TODAY)


def test_budget_for_two_regions_and_multiple_trip_shapes(catalog):
    for region, days, people, budget, scope in product(
        cfg.REGIONS, (1, 3, 5), (1, 3), (1, 450_000, 2_000_000, 10_000_000), ("per_person", "total")
    ):
        plan = make_plan(catalog, region=region, days=days, people=people, budget_vnd=budget, budget_scope=scope)
        if not plan["total_cost_range"]:
            assert plan["errors"]
            continue
        upper = plan["total_cost_range"]["max_vnd"]
        assert 0 <= plan["total_cost_vnd"] <= upper <= plan["budget_vnd"]
        assert upper == sum(row["max_vnd"] for row in plan["cost_breakdown"])
        assert plan["total_cost_vnd"] == sum(row["expected_vnd"] for row in plan["cost_breakdown"])
        assert sum(plan["budget_allocation"].values()) == plan["budget_vnd"]
        assert all(row["travel_minutes"] <= cfg.MAX_TRAVEL_HOURS_PER_DAY * 60 for row in plan["days"])
        ids = [item["place_id"] for day in plan["days"] for item in day["items"]]
        assert len(ids) == len(set(ids))


def test_structured_budget_too_low(catalog):
    plan = make_plan(catalog, budget_vnd=1, budget_scope="total")
    assert plan["total_cost_vnd"] is None and plan["days"] == []
    error, = plan["errors"]
    assert error["code"] == "budget_too_low" and error["minimum_required_vnd"] > 1


@pytest.mark.parametrize("days", [1, 5])
def test_day_boundaries(catalog, days):
    plan = make_plan(catalog, days=days, budget_vnd=12_000_000)
    assert len(plan["days"]) == days
    assert set(plan["days"][0]["slots"]) == {"morning", "afternoon", "evening"}
    if days == 1:
        assert plan["lodging_selected"] is None


def test_live_forecast_changes_plan_but_cache_does_not(catalog, monkeypatch):
    monkeypatch.setattr(weather_service, "CACHE", {})
    baseline = make_plan(catalog)
    date_trip = TODAY
    start = TripRequest("da_nang", 3, 3_000_000, 2, start_date=date_trip)
    calls = []

    def provider(lat, lon, on_date):
        calls.append((lat, lon, on_date))
        return {"source": "forecast", "rain_prob": 0.7 if on_date == TODAY else 0.1}

    def weather(region, date_value, days):
        return weather_service.trip_weather(region, date_value, days, provider=provider, today=TODAY)

    forecast = build_plan(start, catalog=catalog, weather=weather, today=TODAY)
    assert len(calls) == 3
    assert forecast["days"][0]["changed_because"]
    assert all(row["setting"] == "indoor" and not row["rain_sensitive"] for row in forecast["days"][0]["items"])
    assert forecast["total_cost_range"]["max_vnd"] <= forecast["budget_vnd"]

    def error(*_):
        raise OSError("offline")

    cached = weather_service.trip_weather("da_nang", TODAY, 3, provider=error, today=TODAY)
    plan_from_cache = build_plan(start, catalog=catalog, weather=lambda *_: cached, today=TODAY)
    assert cached[0]["source"] == "cache"
    assert plan_from_cache["days"][0]["changed_because"] is None
    assert [d["items"] for d in plan_from_cache["days"]] == [d["items"] for d in baseline["days"]]


def test_severe_rain_holds_the_day(catalog):
    weather = [{"source": "forecast", "rain_prob": 0.9, "severe": True}]
    plan = build_plan(TripRequest("ha_giang", 1, 5_000_000, month=10), catalog=catalog, weather=lambda *_: weather, today=TODAY)
    day, = plan["days"]
    assert day["items"] == []
    assert "Tạm hoãn" in day["changed_because"]


def test_lodging_gap_uses_source_minimum(catalog):
    plan = make_plan(catalog, budget_vnd=1)
    gap = plan["lodging_gap"]
    assert gap["gap_vnd"] == gap["predicted_total"]["min_vnd"] - plan["budget_allocation"]["lodging"]
    assert gap["gap_vnd"] > 0 and not gap["fits_budget"]


def raw_lodging(ident="p1"):
    return {
        "lodging_id": ident, "region": "ha_giang", "name": ident, "type": "homestay",
        "area": "", "lat": "", "lon": "", "tier": "", "rating": "",
        "price_min_vnd": "100", "price_max_vnd": "", "price_unit": "per_person_night",
        "capacity_persons": "3", "source": "https://example.com/rate", "source_date": TODAY.isoformat(),
    }


def test_person_price_normalizes_per_room_and_point_confidence():
    from collections import Counter
    row = raw_lodging()
    lodging = _lodging(row, row, Counter())
    assert lodging["room_price_min_vnd"] == lodging["room_price_max_vnd"] == 300
    assert lodging["price_is_point"] is True
    assert lodging_confidence(lodging, TODAY)[0] == "medium"
    for kind, expected in (("homestay", "unit_unknown"), ("hotel", "per_room_night"), ("guesthouse", "per_room_night")):
        variant = {**row, "type": kind, "price_unit": "", "capacity_persons": ""}
        result = _lodging(variant, variant, Counter())
        assert result["price_unit"] == expected
        if expected == "unit_unknown":
            assert lodging_confidence(result, TODAY)[0] == "low"
    bed = {**row, "price_unit": "giường"}
    result = _lodging(bed, bed, Counter())
    assert result["room_price_min_vnd"] == 100 and result["capacity_persons"] == cfg.ONE_BED_PERSONS
    assert result["price_unit_is_estimate"]


def test_agent_lodging_quotes_respect_price_unit_type_and_upper_bound(monkeypatch):
    from collections import Counter
    from importlib import import_module
    import data_loader

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "codebase"))
    agent = import_module("agent")
    room = raw_lodging("Phòng A") | {"type": "hotel", "tier": "budget", "price_unit": "room_night",
                                     "price_min_vnd": "300000", "price_max_vnd": "500000", "capacity_persons": "2"}
    costly = room | {"lodging_id": "expensive", "name": "Phòng B", "price_max_vnd": "510000"}
    dorm = room | {"lodging_id": "dorm", "name": "Dorm C", "price_unit": "night_unspecified", "rate_kind": "operator_dorm_from"}
    homestay = room | {"lodging_id": "other", "name": "Homestay D", "type": "homestay"}
    rows = [_lodging(raw, raw, Counter()) for raw in (room, costly, dorm, homestay)]
    monkeypatch.setattr(data_loader, "load_data", lambda: Catalog(lodging=rows))
    assert rows[2]["price_unit"] == "unit_unknown" and rows[2]["room_price_max_vnd"] is None

    result = agent.answer("Gợi ý khách sạn Hà Giang cho 3 người 2 đêm, tối đa 500 nghìn/phòng/đêm")["output"]
    assert "Phòng A" in result and "2.000.000 VNĐ" in result
    assert all(name not in result for name in ("Phòng B", "Dorm C", "Homestay D"))

    result = agent.answer("Khách sạn Hà Giang, 3 người, 2 đêm, tổng 1,9 triệu cho cả nhóm")["output"]
    assert "Phòng A" not in result and "vượt 100.000 VNĐ" in result
    prompt = agent.answer("Tìm chỗ ở Hà Giang, 3 người 2 đêm, 500k")["output"]
    assert "giới hạn ngân sách" in prompt


def test_regional_tertiles_count_distinct_properties():
    from collections import Counter
    rows = []
    for idx in range(1, 10):
        source = raw_lodging(str(idx)) | {"price_min_vnd": str(100 * idx)}
        rows.append(_lodging(source, source, Counter()))
    other = rows[0] | {"region": "da_nang", "tier": None}
    _tier_lodging([*rows, other])
    assert [row["tier"] for row in rows] == ["budget"] * 3 + ["mid"] * 3 + ["comfort"] * 3
    assert other["tier"] == "budget" and other["tier_is_estimate"]


def test_output_rejects_invented_prices_and_locations(catalog):
    plan = make_plan(catalog)
    assert validate_output(plan, format_plan(plan))
    assert not validate_output(plan, format_plan(plan) + "\nVé 90.000.000 VNĐ.")
    assert not validate_output(plan, format_plan(plan) + "\nSáng · Phú Quốc")


def test_bedrock_converse_validation_and_error_fallback(catalog):
    plan = make_plan(catalog)
    fallback = format_plan(plan)
    client = Mock()
    client.converse.side_effect = RuntimeError("Bedrock offline")
    assert render_itinerary(plan, client=client, model_id="test.model") == fallback
    assert client.converse.call_args.kwargs["modelId"] == "test.model"
    client.converse.side_effect = None
    client.converse.return_value = {"output": {"message": {"content": [{"text": "Đi Paris, giá 90 triệu."}]}}}
    assert render_itinerary(plan, client=client, model_id="test.model") == fallback
    approved = next(line for line in fallback.splitlines() if line.startswith("Chỗ ở"))
    client.converse.return_value = {"output": {"message": {"content": [{"text": approved}]}}}
    assert render_itinerary(plan, client=client, model_id="test.model") == approved


def test_sparse_region_degrades_to_lodging(catalog):
    sparse = Catalog(lodging=catalog.lodging, costs=catalog.costs)
    plan = make_plan(sparse)
    assert plan["mode"] == "lodging_only" and plan["days"] == []
    assert plan["lodging_selected"] is not None


def test_loader_rejects_missing_columns_and_uses_local_fallback(tmp_path, monkeypatch):
    import shutil
    import data_loader
    for filename in ("places.csv", "costs.csv", "routes.csv"):
        shutil.copy(data_loader.DATA_PATH / filename, tmp_path)
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setattr(data_loader, "_load_s3", Mock(side_effect=OSError("S3 offline")))
    catalog = load_data(tmp_path)
    assert catalog.source == "local" and not validate_data(catalog)
    assert make_plan(catalog)["lodging_selected"] is not None
    (tmp_path / "places.csv").write_text("bad,header\na,b\n")
    with pytest.raises(ValueError, match="thiếu cột"):
        load_data(tmp_path)


def test_optional_duration_override_and_foreign_rows(tmp_path):
    import shutil
    import data_loader
    for filename in ("places.csv", "costs.csv", "routes.csv"):
        shutil.copy(data_loader.DATA_PATH / filename, tmp_path)
    data = tmp_path / "places.csv"
    with data.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        first = next(reader)
    with data.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=fields).writerow(first | {"id": "X01", "thanh_pho": "outside"})
    (tmp_path / "duration_overrides.csv").write_text("place_id,duration_hours,source\nH02,1.25,guide\n")
    loaded = load_data(tmp_path, use_s3=False)
    assert loaded.audit["outside/places/outside"] == 1
    overridden = next(row for row in loaded.places if row["place_id"] == "H02")
    assert overridden["duration_hours"] == 1.25 and not overridden["duration_is_estimate"]
    assert next(row for row in loaded.places if row["place_id"] == "H09")["duration_is_estimate"]


def test_allocation_preserves_rounding():
    for style in cfg.BUDGET_SPLIT:
        assert sum(allocate_budget(11, style).values()) == 11


def test_streamlit_form_works_without_external_services(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=12)
    assert not app.exception
    assert app.session_state["vietdu"] == {}
