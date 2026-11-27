"""Tích hợp weather.py do nhóm cung cấp và giữ nguyên nhãn nguồn."""
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from importlib import import_module
from math import isfinite
from threading import Lock

import config as cfg

CACHE = {}
CACHE_LOCK = Lock()


def _provider():
    try:
        provider = import_module("weather").get_weather
        return provider if callable(provider) else None
    except (ImportError, AttributeError):
        return None


def unavailable(day):
    return {
        "date": day.isoformat() if day else None, "source": "unavailable", "source_date": None,
        "rain_prob": None, "is_estimate": False, "confidence": "low", "severe": False,
    }


def _normalize(day, value, today):
    result = unavailable(day)
    if not isinstance(value, dict) or value.get("error"):
        return result
    source = value.get("source")
    if source not in {"forecast", "climatology", "cache"}:
        return result
    if source == "forecast" and not 0 <= (day - today).days < cfg.FORECAST_DAYS:
        return result
    try:
        raw_probability = value.get("rain_prob")
        probability = None if isinstance(raw_probability, bool) else float(raw_probability)
    except (KeyError, TypeError, ValueError):
        probability = None
    if probability is None or not isfinite(probability) or not 0 <= probability <= 1:
        return result
    result.update(source=source, source_date=value.get("source_date") or today.isoformat(),
                  rain_prob=probability, is_estimate=True,
                  confidence="medium" if source == "forecast" else "low",
                  severe=source == "forecast" and (value.get("severe") is True or probability >= cfg.SEVERE_RAIN_PROBABILITY))
    return result


def _cached(key, day, today):
    with CACHE_LOCK:
        result = CACHE.get(key)
        if result is not None and 0 <= (day - today).days < cfg.FORECAST_DAYS:
            return {**result, "source": "cache", "confidence": "low", "severe": False}
    return unavailable(day)


def trip_weather(region, start_date, days, *, provider=None, today=None):
    if start_date is None:
        return [unavailable(None) for _ in range(days)]
    dates = [start_date + timedelta(days=index) for index in range(days)]
    provider = _provider() if provider is None else provider
    if provider is None:
        return [unavailable(day) for day in dates]
    today = today or datetime.now(cfg.TIMEZONE).date()
    latitude, longitude = cfg.REGIONS[region]
    executor = ThreadPoolExecutor(max_workers=min(days, cfg.MAX_DAYS))
    futures = {day: executor.submit(provider, latitude, longitude, day) for day in dates}
    wait(futures.values(), timeout=cfg.WEATHER_TIMEOUT_SECONDS)
    result = []
    try:
        for day, future in futures.items():
            key = region, day
            payload = unavailable(day)
            if future.done():
                try:
                    payload = _normalize(day, future.result(), today)
                except Exception:
                    pass  # Lỗi nguồn thời tiết đi theo nhánh cache/unavailable.
            if payload["source"] == "forecast":
                with CACHE_LOCK:
                    for expired in [item for item in CACHE if item[1] < today]:
                        del CACHE[expired]
                    CACHE[key] = payload
            if payload["source"] == "unavailable":
                payload = _cached(key, day, today)
            result.append(payload)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return result
