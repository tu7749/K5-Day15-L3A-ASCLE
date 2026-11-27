"""Open-Meteo forecast and a five-year same-month reanalysis for Việt Du."""
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from functools import lru_cache
import json
from math import isfinite
from time import time
from urllib.parse import urlencode
from urllib.request import urlopen

from config import FORECAST_DAYS, TIMEZONE

FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
DAILY = ("temperature_2m_min", "temperature_2m_max", "precipitation_sum",
         "precipitation_probability_max", "weather_code")
TIMEOUT_SECONDS = 4
CACHE_SECONDS = 900
HISTORY_YEARS = 5
WET_DAY_MM = 1


def _get(endpoint, parameters):
    query = urlencode(parameters | {"timezone": "Asia/Ho_Chi_Minh"})
    with urlopen(f"{endpoint}?{query}", timeout=TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    if payload.get("error") or not isinstance(payload.get("daily"), dict):
        raise ValueError("Open-Meteo did not return daily data")
    return payload["daily"]


def _number(value):
    return value if type(value) in (int, float) and isfinite(value) else None


@lru_cache(maxsize=256)
def _forecast(lat, lon, day, bucket):
    daily = _get(FORECAST, {
        "latitude": lat, "longitude": lon, "daily": ",".join(DAILY),
        "start_date": day.isoformat(), "end_date": day.isoformat(),
    })
    index = daily["time"].index(day.isoformat())
    values = [_number(daily[field][index]) for field in DAILY]
    if all(value is None for value in values):
        raise ValueError("Empty forecast")
    low, high, rain, chance, code = values
    return {"source": "forecast", "source_url": FORECAST, "temperature_min": low, "temperature_max": high,
            "rain_mm": rain, "rain_probability": chance, "weather_code": code}


@lru_cache(maxsize=128)
def _history(lat, lon, month, last_year, bucket):
    first_year = last_year - HISTORY_YEARS + 1
    daily = _get(ARCHIVE, {
        # ERA5 includes coastal grid cells. ERA5-Land can return only nulls around Đà Nẵng.
        "latitude": lat, "longitude": lon, "daily": "precipitation_sum", "models": "era5",
        "start_date": date(first_year, 1, 1).isoformat(), "end_date": date(last_year, 12, 31).isoformat(),
    })
    dates = [date.fromisoformat(value) for value in daily["time"]]
    wanted = {day: _number(mm) for day, mm in zip(dates, daily["precipitation_sum"])
              if day.month == month and first_year <= day.year <= last_year}
    expected = sum(monthrange(year, month)[1] for year in range(first_year, last_year + 1))
    if len(wanted) != expected or any(value is None or value < 0 for value in wanted.values()):
        raise ValueError("Incomplete historical month coverage")
    return {"source": "history", "source_url": ARCHIVE, "wet_days": sum(mm >= WET_DAY_MM for mm in wanted.values()),
            "total_days": expected, "reference_start": first_year, "reference_end": last_year}


def daily_weather(lat, lon, day, *, today=None):
    today = today or datetime.now(TIMEZONE).date()
    # Cụm tham quan làm tròn 0,01° để tái sử dụng phản hồi trong cùng khu vực.
    coordinates = round(lat, 2), round(lon, 2)
    if day < today:
        return {"source": "unavailable"}
    try:
        if (day - today).days < FORECAST_DAYS:
            return _forecast(*coordinates, day, int(time() // CACHE_SECONDS))
        # Gộp cache theo tháng và giai đoạn, dữ liệu quá khứ thay đổi chậm.
        return _history(*coordinates, day.month, today.year - 1, int(time() // 86_400))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return {"source": "unavailable"}


def trip_weather(requests):
    with ThreadPoolExecutor(max_workers=max(1, len(requests))) as executor:
        return list(executor.map(lambda request: daily_weather(*request), requests))
