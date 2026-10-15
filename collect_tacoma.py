"""Tacoma CHEG807 forecast acquisition + figure generator.

Uses the same Open-Meteo six hourly variables as the professor's MATLAB
48-hour forecast script. TEST can run any time; COLLECT saves official
snapshots only when Delaware-local request and finish times are 07:30-08:30.
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fetch_forecast import COLUMNS as BASE_COLUMNS
from fetch_forecast import UD_TZ, build_rows, download

CITY = {
    "city": "Tacoma, WA",
    "latitude": 47.2529,
    "longitude": -122.4443,
    "timezone": "America/Los_Angeles",
}
CITY_TZ = ZoneInfo(CITY["timezone"])
COLUMNS = BASE_COLUMNS.copy()
COLUMNS.insert(COLUMNS.index("capture_time_ud") + 1, "capture_time_city")

OFFICIAL = Path("data/tacoma")
SNAPSHOTS = OFFICIAL / "snapshots"
PLOTS = OFFICIAL / "plots"
TEST_DIR = Path("test-output/tacoma")


def in_assignment_window(instant):
    t = instant.astimezone(UD_TZ)
    return 7 * 60 + 30 <= t.hour * 60 + t.minute < 8 * 60 + 30


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def plot_forecast(rows, chart_path):
    """Professor-equivalent plot: forecast hour versus rain probability."""
    import matplotlib
    matplotlib.use("Agg")  # Render in GitHub Actions without a desktop.
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(12, 5))
    for day in ("day1", "day2"):
        selected = [r for r in rows if r["forecast_day"] == day]
        xs = [datetime.fromisoformat(r["forecast_time_city"]) for r in selected]
        ys = [float(r["rain_chance_pct"]) if r["rain_chance_pct"] != "" else float("nan")
              for r in selected]
        ax.plot(xs, ys, marker=".", linewidth=1.5, label=day.upper())
    ax.set(
        title=("Tacoma hourly precipitation probability\n"
               f"Captured: {rows[0]['capture_time_city']} (Tacoma local time)"),
        xlabel="Forecast time (Tacoma local)",
        ylabel="Probability of precipitation (%)",
        ylim=(-2, 102),
    )
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(tz=CITY_TZ))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M", tz=CITY_TZ))
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(chart_path, dpi=160)
    plt.close(fig)


def rebuild_day_tables():
    by_day = {"day1": [], "day2": []}
    for file in sorted(SNAPSHOTS.glob("*.csv")):
        with file.open(newline="", encoding="utf-8") as source:
            for record in csv.DictReader(source):
                if record["forecast_day"] not in by_day:
                    raise ValueError(f"Unrecognized forecast_day in {file}")
                by_day[record["forecast_day"]].append(record)
    for day, records in by_day.items():
        target = OFFICIAL / f"{day}_forecasts.csv"
        save_csv(target, records)
        print(f"Updated {target}: {len(records)} hourly rows")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "collect"], default="test")
    args = parser.parse_args()
    captured = datetime.now(timezone.utc)
    capture_ud = captured.astimezone(UD_TZ)
    capture_city = captured.astimezone(CITY_TZ)

    print(f"City: {CITY['city']} ({CITY['latitude']}, {CITY['longitude']})")
    print(f"Request started (Delaware): {capture_ud.isoformat(timespec='seconds')}")
    print(f"Request started (Tacoma): {capture_city.isoformat(timespec='seconds')}")
    print(f"Run mode: {args.mode}")

    day_name = capture_ud.strftime("%Y-%m-%d")
    output_csv = SNAPSHOTS / f"{day_name}.csv"
    output_plot = PLOTS / f"{day_name}.png"

    if args.mode == "collect":
        if not in_assignment_window(captured):
            raise RuntimeError("Outside 07:30-08:30 America/New_York; no official CSV saved.")
        if output_csv.exists():
            print(f"Official snapshot already exists: {output_csv}; not overwriting.")
            return

    # Same Open-Meteo API, six variables, and hourly classification logic
    # used by the tested Python implementation of the professor forecast code.
    rows = build_rows(download(CITY), CITY, captured)
    for row in rows:
        row["capture_time_city"] = capture_city.isoformat(timespec="seconds")
    print(f"Rows: {len(rows)}, Day 1: {sum(r['forecast_day']=='day1' for r in rows)}, "
          f"Day 2: {sum(r['forecast_day']=='day2' for r in rows)}")

    if args.mode == "test":
        save_csv(TEST_DIR / "forecast_test.csv", rows)
        plot_forecast(rows, TEST_DIR / "forecast_test.png")
        print("TEST results available as downloadable artifacts; no official files changed.")
        return

    if not in_assignment_window(datetime.now(timezone.utc)):
        raise RuntimeError("API call finished after 08:30 Delaware time; not saving.")

    save_csv(output_csv, rows)
    plot_forecast(rows, output_plot)
    rebuild_day_tables()
    print(f"OFFICIAL CSV saved: {output_csv}")
    print(f"OFFICIAL PLOT saved: {output_plot}")


if __name__ == "__main__":
    main()
