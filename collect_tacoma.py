"""CHEG 807 Tacoma: faithful Open-Meteo 48-hour forecast collection.

Implements every functional step in the professor's 'Grab Weather Data Next
2 Days.m': request six hourly fields from the Forecast API, keep a rolling
48-hour window, retain capture + forecast time, append a MATLAB-compatible
forecast log, and plot the hourly precipitation probability. Also preserves
raw six-field CSV snapshots and derived day1/day2 tables for the assignment.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API = "https://api.open-meteo.com/v1/forecast"
CITY_NAME = "Tacoma, WA"
LATITUDE = 47.2529
LONGITUDE = -122.4443
CITY_TIMEZONE = "America/Los_Angeles"
COLLECTION_TIMEZONE = "America/New_York"  # For Delaware timestamps/date only; execution time is controlled externally
CITY_TZ = ZoneInfo(CITY_TIMEZONE)
COLLECT_TZ = ZoneInfo(COLLECTION_TIMEZONE)
FORECAST_FIELDS = (
    "temperature_2m", "precipitation_probability", "precipitation",
    "relative_humidity_2m", "wind_speed_10m", "weather_code",
)
ROOT = Path("data/tacoma")
SNAPSHOTS = ROOT / "snapshots"
PLOTS = ROOT / "plots"
TEST_ROOT = Path("test-output/tacoma/forecast")

# Keep existing rich CSV fields stable; add the requested Tacoma capture time.
COLUMNS = [
    "capture_time_utc", "capture_time_ud", "capture_time_city",
    "forecast_time_utc", "forecast_time_city", "forecast_day",
    "hours_ahead_from_current_hour", "rain_chance_pct", "temperature_c",
    "forecast_precip_mm", "relative_humidity_pct", "wind_speed_kmh",
    "weather_code", "city", "latitude", "longitude", "city_timezone", "source",
]
MATLAB_FORECAST_COLUMNS = ["currTime", "ForecastTime", "Temp_C", "RainChance_pct"]


def api_get(query: dict) -> dict:
    """GET JSON with short retries; never invent or backfill earlier forecasts."""
    url = API + "?" + urlencode(query)
    last = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "CHEG807-Tacoma-weather/2.0"})
            with urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            if data.get("error") or "hourly" not in data:
                raise ValueError(f"Open-Meteo response: {data}")
            return data
        except (OSError, ValueError, KeyError) as exc:
            last = exc
            print(f"Open-Meteo attempt {attempt+1}/3 failed: {exc}")
            if attempt < 2:
                time.sleep(5 * (attempt+1))
    raise RuntimeError(f"Open-Meteo request unsuccessful: {last}")


def get_forecast() -> dict:
    # Same fields and forecast_days=3 as professor's MATLAB code.
    # Unix times avoid ambiguous duplicate local hours when DST ends.
    return api_get({
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "forecast_days": 3, "hourly": ",".join(FORECAST_FIELDS),
        "timezone": CITY_TIMEZONE, "timeformat": "unixtime",
    })


def make_forecast_rows(data: dict, captured: datetime) -> list[dict]:
    h = data["hourly"]
    fields = ("time",) + FORECAST_FIELDS
    if any(k not in h for k in fields):
        raise ValueError("Missing hourly variable from forecast API response")
    n = len(h["time"])
    if any(len(h[k]) != n for k in fields):
        raise ValueError("Inconsistent number of hourly values in API response")
    if captured.tzinfo is None:
        raise ValueError("The capture time must include a timezone")

    local_capture = captured.astimezone(CITY_TZ)
    local_collect = captured.astimezone(COLLECT_TZ)
    current_hour_utc = int(captured.timestamp()) // 3600 * 3600
    selected = []
    for i, raw in enumerate(h["time"]):
        timestamp = int(raw)
        if not (current_hour_utc <= timestamp < current_hour_utc + 48 * 3600):
            continue
        forecast_utc = datetime.fromtimestamp(timestamp, timezone.utc)
        forecast_city = forecast_utc.astimezone(CITY_TZ)
        local_date_offset = (forecast_city.date() - local_capture.date()).days
        # An early-morning forecast legitimately includes some of a third day.
        # Crucially do not discard that information from the raw snapshot.
        label = f"day{local_date_offset+1}"

        def val(k):
            result = h[k][i]
            return "" if result is None else result

        selected.append({
            "capture_time_utc": captured.isoformat(timespec="seconds"),
            "capture_time_ud": local_collect.isoformat(timespec="seconds"),
            "capture_time_city": local_capture.isoformat(timespec="seconds"),
            "forecast_time_utc": forecast_utc.isoformat(timespec="seconds"),
            "forecast_time_city": forecast_city.isoformat(timespec="seconds"),
            "forecast_day": label,
            "hours_ahead_from_current_hour": (timestamp-current_hour_utc)//3600,
            "rain_chance_pct": val("precipitation_probability"),
            "temperature_c": val("temperature_2m"),
            "forecast_precip_mm": val("precipitation"),
            "relative_humidity_pct": val("relative_humidity_2m"),
            "wind_speed_kmh": val("wind_speed_10m"),
            "weather_code": val("weather_code"),
            "city": CITY_NAME, "latitude": LATITUDE, "longitude": LONGITUDE,
            "city_timezone": CITY_TIMEZONE, "source": "Open-Meteo Forecast API",
        })
    if len(selected) != 48:
        raise ValueError(f"Expected all 48 rolling forecast hours; obtained {len(selected)}")
    if not any(row["forecast_day"] == "day1" for row in selected):
        raise ValueError("No day1 forecasts in 48-hour window")
    if not any(row["forecast_day"] == "day2" for row in selected):
        raise ValueError("No day2 forecasts in 48-hour window")
    return selected


def write_csv(filename: Path, rows: list[dict], columns: list[str] = COLUMNS) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def plot_forecast(rows: list[dict], filename: Path) -> None:
    # Matches professor's figure() + plot(F.ForecastTime,F.RainChance_pct)
    # + grid/title/ylabel, with explicit local-time axis and day markers.
    import matplotlib
    matplotlib.use("Agg")  # Required in headless GitHub Actions runner
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    xs = [datetime.fromisoformat(r["forecast_time_city"]) for r in rows]
    ys = [float(r["rain_chance_pct"]) if r["rain_chance_pct"] != "" else float("nan")
          for r in rows]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(xs, ys, marker=".", linewidth=1.5)
    ax.grid(True)
    ax.set_title("Hourly precipitation against day — Tacoma, WA")
    ax.set_ylabel("% Likelihood of rain")
    ax.set_xlabel("Forecast hour (Tacoma local time)")
    ax.set_ylim(-2, 102)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(tz=CITY_TZ))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M", tz=CITY_TZ))
    fig.autofmt_xdate()
    fig.tight_layout()
    filename.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filename, dpi=160)
    plt.close(fig)


def as_matlab_rows(records: list[dict]) -> list[dict]:
    """Reproduce professor's exact four-column append-style CSV projection."""
    output = []
    for r in records:
        local_capture = datetime.fromisoformat(r["capture_time_city"])
        forecast_local = datetime.fromisoformat(r["forecast_time_city"])
        output.append({
            "currTime": local_capture.strftime("%Y-%m-%d %H:%M"),
            "ForecastTime": forecast_local.strftime("%Y-%m-%d %H:%M"),
            "Temp_C": r["temperature_c"],
            "RainChance_pct": r["rain_chance_pct"],
        })
    return output


def rebuild_outputs() -> None:
    """Replay snapshots to generate duplicate-free cumulative CSVs."""
    batches = {"day1": [], "day2": [], "day3": []}
    all_rows = []
    for file in sorted(SNAPSHOTS.glob("*.csv")):
        with file.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                if record["city"] != CITY_NAME:
                    raise ValueError(f"Foreign city's data found in {file}")
                all_rows.append(record)
                batches.setdefault(record["forecast_day"], []).append(record)
    for day in ("day1", "day2", "day3"):
        write_csv(ROOT / f"{day}_forecasts.csv", batches[day])
    write_csv(ROOT / "forecast_log_matlab_compatible.csv",
              as_matlab_rows(all_rows), MATLAB_FORECAST_COLUMNS)
    print(f"Cumulative MATLAB-compatible forecast log: {len(all_rows)} rows")
    print("Same-day prediction hours:", len(batches["day1"]))
    print("Next-day prediction hours:", len(batches["day2"]))
    print("Third-calendar-day tail hours (preserved):", len(batches["day3"]))



def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("test", "collect"), default="test")
    args = parser.parse_args()
    captured = datetime.now(timezone.utc)
    date_name = captured.astimezone(COLLECT_TZ).strftime("%Y-%m-%d")
    target = SNAPSHOTS / f"{date_name}.csv"

    print(f"City: {CITY_NAME}; coordinates: {LATITUDE}, {LONGITUDE}")
    print(f"Capture (Delaware): {captured.astimezone(COLLECT_TZ).isoformat(timespec='seconds')}")
    print(f"Capture (Tacoma): {captured.astimezone(CITY_TZ).isoformat(timespec='seconds')}")
    if args.mode == "collect":
        if target.exists():
            print(f"Official snapshot exists: {target}. Will not overwrite today's forecast.")
            return

    rows = make_forecast_rows(get_forecast(), captured)
    print(f"Forecast returned {len(rows)} hourly records; first: {rows[0]['forecast_time_city']}; "
          f"last: {rows[-1]['forecast_time_city']}")
    if args.mode == "test":
        write_csv(TEST_ROOT / "forecast_test_full48.csv", rows)
        write_csv(TEST_ROOT / "forecast_test_matlab_format.csv",
                  as_matlab_rows(rows), MATLAB_FORECAST_COLUMNS)
        plot_forecast(rows, TEST_ROOT / "forecast_test.png")
        print("TEST ONLY — CSV and PNG saved as workflow artifact; not official data")
        return

    # Render figure first, so plotting errors do not create a partial snapshot.
    plot_forecast(rows, PLOTS / f"{date_name}.png")
    write_csv(target, rows)
    rebuild_outputs()
    print(f"Saved official snapshot {target} and figure {PLOTS / f'{date_name}.png'}")


if __name__ == "__main__":
    main()
