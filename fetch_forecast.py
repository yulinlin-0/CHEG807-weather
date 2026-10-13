"""CHEG 807 Project A: collect timestamped Open-Meteo forecasts.

Run in test mode to inspect a forecast without saving official observations.
Scheduled mode only saves one snapshot per Delaware date if the forecast was
collected between 07:30 and 08:30 America/New_York.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API = "https://api.open-meteo.com/v1/forecast"
UD_TZ = ZoneInfo("America/New_York")
VARIABLES = (
    "temperature_2m",
    "precipitation_probability",
    "precipitation",
    "relative_humidity_2m",
    "wind_speed_10m",
    "weather_code",
)
COLUMNS = [
    "capture_time_utc", "capture_time_ud",
    "forecast_time_utc", "forecast_time_city",
    "forecast_day", "hours_ahead_from_current_hour",
    "rain_chance_pct", "temperature_c",
    "forecast_precip_mm", "relative_humidity_pct",
    "wind_speed_kmh", "weather_code",
    "city", "latitude", "longitude", "city_timezone", "source",
]


def settings():
    return {
        "city": os.getenv("CITY_NAME", "Seattle, WA (TEST ONLY)"),
        "latitude": float(os.getenv("LATITUDE", "47.6062")),
        "longitude": float(os.getenv("LONGITUDE", "-122.3321")),
        "timezone": os.getenv("CITY_TIMEZONE", "America/Los_Angeles"),
    }


def download(cfg):
    query = urlencode({
        "latitude": cfg["latitude"],
        "longitude": cfg["longitude"],
        "forecast_days": 3,
        "hourly": ",".join(VARIABLES),
        "timezone": cfg["timezone"],
        "timeformat": "unixtime",
    })
    error = None
    for attempt in range(3):
        try:
            request = Request(
                API + "?" + query,
                headers={"User-Agent": "CHEG807-weather-collection/1.0"},
            )
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
            if "hourly" not in data or "time" not in data["hourly"]:
                raise ValueError("Open-Meteo returned no hourly forecast data.")
            return data
        except (OSError, ValueError, KeyError) as exc:
            error = exc
            print(f"Attempt {attempt + 1}/3 failed: {exc}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve forecast: {error}")


def build_rows(data, cfg, captured):
    hourly = data["hourly"]
    required = ["time", *VARIABLES]
    if any(field not in hourly for field in required):
        raise ValueError("API response is missing one of the requested weather variables.")
    n = len(hourly["time"])
    if any(len(hourly[field]) != n for field in required):
        raise ValueError("Inconsistent hourly array lengths.")

    city_tz = ZoneInfo(cfg["timezone"])
    city_day = captured.astimezone(city_tz).date()
    start_hour = (int(captured.timestamp()) // 3600) * 3600
    rows = []
    for i, raw_timestamp in enumerate(hourly["time"]):
        timestamp = int(raw_timestamp)
        if not start_hour <= timestamp < start_hour + 48 * 3600:
            continue
        forecast_utc = datetime.fromtimestamp(timestamp, timezone.utc)
        forecast_local = forecast_utc.astimezone(city_tz)
        offset = (forecast_local.date() - city_day).days
        if offset not in (0, 1):
            continue

        def value(key):
            v = hourly[key][i]
            return "" if v is None else v

        rows.append({
            "capture_time_utc": captured.isoformat(timespec="seconds"),
            "capture_time_ud": captured.astimezone(UD_TZ).isoformat(timespec="seconds"),
            "forecast_time_utc": forecast_utc.isoformat(timespec="seconds"),
            "forecast_time_city": forecast_local.isoformat(timespec="seconds"),
            "forecast_day": f"day{offset + 1}",
            "hours_ahead_from_current_hour": (timestamp - start_hour) // 3600,
            "rain_chance_pct": value("precipitation_probability"),
            "temperature_c": value("temperature_2m"),
            "forecast_precip_mm": value("precipitation"),
            "relative_humidity_pct": value("relative_humidity_2m"),
            "wind_speed_kmh": value("wind_speed_10m"),
            "weather_code": value("weather_code"),
            "city": cfg["city"],
            "latitude": cfg["latitude"],
            "longitude": cfg["longitude"],
            "city_timezone": cfg["timezone"],
            "source": "Open-Meteo Forecast API",
        })
    if not any(r["forecast_day"] == "day1" for r in rows):
        raise ValueError("Missing same-day forecast.")
    if not any(r["forecast_day"] == "day2" for r in rows):
        raise ValueError("Missing next-day forecast.")
    return rows


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def rebuild(snapshots):
    batches = {"day1": [], "day2": []}
    for file in sorted(snapshots.glob("*.csv")):
        with file.open(encoding="utf-8", newline="") as source:
            for record in csv.DictReader(source):
                batches[record["forecast_day"]].append(record)
    for label, records in batches.items():
        dest = Path("data") / f"{label}_forecasts.csv"
        save_csv(dest, records)
        print(f"Wrote {dest}: {len(records)} rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "scheduled"], default="test")
    args = parser.parse_args()
    cfg = settings()
    ZoneInfo(cfg["timezone"])  # Fail early if city timezone is invalid.
    captured = datetime.now(timezone.utc)
    local_ud = captured.astimezone(UD_TZ)
    print(f"Mode={args.mode}; city={cfg['city']}")
    print(f"Captured at {local_ud.isoformat(timespec='seconds')} Delaware time")

    if args.mode == "scheduled":
        minute_of_day = local_ud.hour * 60 + local_ud.minute
        if not 450 <= minute_of_day < 510:
            raise RuntimeError("Outside the required 07:30-08:30 Delaware capture window")
        snapshots = Path("data") / "snapshots"
        output = snapshots / f"{local_ud:%Y-%m-%d}.csv"
        if output.exists():
            print("Today's snapshot already exists; preserving original capture.")
            return

    rows = build_rows(download(cfg), cfg, captured)
    print("Forecast rows:", len(rows))
    print("Day 1:", sum(r["forecast_day"] == "day1" for r in rows))
    print("Day 2:", sum(r["forecast_day"] == "day2" for r in rows))

    if args.mode == "test":
        save_csv(Path("test-output") / "forecast_test.csv", rows)
        print("TEST: forecast saved only as an Actions artifact.")
        return

    finished_ud = datetime.now(timezone.utc).astimezone(UD_TZ)
    finished_minutes = finished_ud.hour * 60 + finished_ud.minute
    if not 450 <= finished_minutes < 510:
        raise RuntimeError("Data acquisition finished after 08:30; not saving")
    save_csv(output, rows)
    rebuild(snapshots)
    print(f"SUCCESS: saved {output}")


if __name__ == "__main__":
    main()
