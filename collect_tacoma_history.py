"""Professor's Grab Weather Data Last 30 Days.m equivalent for Tacoma.

Reproduces professor's Open-Meteo forecast endpoint, 5 requested fields,
past 30 local calendar days ending yesterday, Time/Temp_C/Precip_mm CSV,
head(T,20) console preview, and hourly precipitation-versus-time figure.
Also saves all five queried meteorological variables separately.
Past values from forecast API are NOT validated independent station observations.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from collect_tacoma import (
    API, CITY_NAME, LATITUDE, LONGITUDE, CITY_TIMEZONE, CITY_TZ,
    ROOT, api_get, write_csv,
)
HISTORY_VARS = ("temperature_2m", "relative_humidity_2m", "precipitation",
                "wind_speed_10m", "weather_code")
HISTORY_ROOT = ROOT / "history"
TEST_ROOT = Path("test-output/tacoma/history")
MATLAB_COLUMNS = ["Time", "Temp_C", "Precip_mm"]
ALL_COLUMNS = [
    "Time", "Time_utc", "Temp_C", "Precip_mm", "RelativeHumidity_pct",
    "WindSpeed_kmh", "WeatherCode", "rain_occurrence_gt_0mm", "city",
    "latitude", "longitude", "timezone", "source", "acquired_at_utc",
]


def fetch_history(days, captured):
    if days < 1 or days > 92:
        raise ValueError("Number of days must be between 1 and 92")
    end = captured.astimezone(CITY_TZ).date() - timedelta(days=1)
    start = end - timedelta(days=days-1)
    data = api_get({
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "hourly": ",".join(HISTORY_VARS), "timezone": CITY_TIMEZONE,
        "timeformat": "unixtime",
    })
    return data, start.isoformat(), end.isoformat()


def make_rows(data, captured):
    h = data["hourly"]
    fields = ("time",) + HISTORY_VARS
    if any(field not in h for field in fields):
        raise ValueError("Historical API response missing required variables")
    n = len(h["time"])
    if any(len(h[field]) != n for field in fields):
        raise ValueError("Historical hourly variable lengths differ")
    output = []
    for i, raw in enumerate(h["time"]):
        stamp = datetime.fromtimestamp(int(raw), timezone.utc)
        local = stamp.astimezone(CITY_TZ)
        def val(name):
            value = h[name][i]
            return "" if value is None else value
        precip = val("precipitation")
        output.append({
            "Time": local.strftime("%Y-%m-%d %H:%M"),
            "Time_utc": stamp.isoformat(timespec="seconds"),
            "Temp_C": val("temperature_2m"),
            "Precip_mm": precip,
            "RelativeHumidity_pct": val("relative_humidity_2m"),
            "WindSpeed_kmh": val("wind_speed_10m"),
            "WeatherCode": val("weather_code"),
            "rain_occurrence_gt_0mm": "" if precip == "" else int(float(precip)>0),
            "city": CITY_NAME, "latitude": LATITUDE, "longitude": LONGITUDE,
            "timezone": CITY_TIMEZONE,
            "source": "Open-Meteo Forecast API (model-derived past; not verified station observation)",
            "acquired_at_utc": captured.isoformat(timespec="seconds"),
        })
    if not output:
        raise ValueError("No past hourly data returned")
    return output


def plot_history(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    dates = [datetime.fromisoformat(row["Time_utc"]).astimezone(CITY_TZ) for row in rows]
    amounts = [float(row["Precip_mm"]) if row["Precip_mm"] != "" else float("nan") for row in rows]
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(dates, amounts)
    ax.grid(True)
    ax.set_title("Hourly precipitation against day — Tacoma, WA")
    ax.set_xlabel("Hour (Tacoma local time)")
    ax.set_ylabel("mm")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(tz=CITY_TZ))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M", tz=CITY_TZ))
    fig.autofmt_xdate()
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("test", "collect"), default="test")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    captured = datetime.now(timezone.utc)
    data, start, end = fetch_history(args.days, captured)
    rows = make_rows(data, captured)

    print(f"City: {CITY_NAME} ({LATITUDE}, {LONGITUDE}); timezone: {CITY_TIMEZONE}")
    print(f"Professor's original endpoint: {API}")
    print(f"Date range (Tacoma): {start} through {end}")
    print(f"Hourly records: {len(rows)}")
    print("head(T, 20):")
    print(", ".join(MATLAB_COLUMNS))
    for row in rows[:20]:
        print(", ".join(str(row[k]) for k in MATLAB_COLUMNS))

    folder = TEST_ROOT if args.mode == "test" else HISTORY_ROOT
    name = f"{start}_to_{end}"
    simple = folder / f"{name}_matlab_format.csv"
    full = folder / f"{name}_all_variables.csv"
    fig = folder / f"{name}_precipitation.png"
    write_csv(simple, [{k: row[k] for k in MATLAB_COLUMNS} for row in rows], MATLAB_COLUMNS)
    write_csv(full, rows, ALL_COLUMNS)
    plot_history(rows, fig)
    print(f"Saved: {simple}, {full}, {fig}")
    print("Warning: this API does not guarantee independent measured rain observations.")


if __name__ == "__main__":
    main()
