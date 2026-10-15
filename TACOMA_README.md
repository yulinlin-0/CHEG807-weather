# Tacoma — two professor MATLAB scripts recreated in Python

The original MATLAB files are preserved under `professor_matlab/original/`. These Python scripts implement the functionality of **both** supplied MATLAB scripts (same Open-Meteo forecast endpoint and respective requested variables), while adding daily GitHub storage, city-local capture timestamps, all-variable CSV exports, and saved PNG figures.

## Scripts and equivalence

| Professor MATLAB | Python | API variables | Outputs |
|---|---|---|---|
| Grab Weather Data Next 2 Days.m | `collect_tacoma.py` | temperature_2m, precipitation_probability, precipitation, relative_humidity_2m, wind_speed_10m, weather_code | 48-hour raw snapshot, four-column MATLAB-format cumulative log, day1/day2/day3 cumulative spreadsheets, hourly rain-probability PNG |
| Grab Weather Data Last 30 Days.m | `collect_tacoma_history.py` | temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m, weather_code | Past 30 days ending yesterday, three-column MATLAB-format CSV, enriched CSV with all requested fields, hourly precipitation PNG, first 20 rows in GitHub log |

**Forecast time definitions:** rolling 48 hourly forecast timestamps starting at the capture hour. The same local calendar day is `day1`, next local calendar day is `day2`, and the remainder may fall on `day3`. This tail is preserved, unlike the first test script which discarded it. The professor's four-column CSV format is available in `data/tacoma/forecast_log_matlab_compatible.csv`. Daily snapshots contain additional full API fields.

**Difference from original MATLAB:** The original forecast script appends directly to one CSV; we reconstruct that cumulative CSV from immutable daily snapshots to avoid duplicate writes and support audits. The original last-30-days script overwrites its named CSV; our run-stamped date-range files prevent losing previous outputs. These are intentional storage upgrades, not omitted functionality.

**Timezone:** `capture_time_ud` is America/New_York; `capture_time_city` and `forecast_time_city` are America/Los_Angeles. The external 7:30 AM schedule is **Delaware time**, equivalent to **Tacoma 4:30 AM** during daylight saving time. If course requirements instead refer to city-local 7:30 AM, change the external scheduler, AND the official collector's collection-timezone/window guard.

## GitHub workflow and cron-job.org

Action: `.github/workflows/collect_tacoma.yml`, manually dispatchable, with input `mode` and `task`.

- **Preview forecast:** `mode=test, task=forecast`. Saved as workflow artifact `tacoma-forecast-preview` (CSV + PNG) only.
- **Official forecast:** `mode=collect, task=forecast`. Saves one daily snapshot and PNG between 7:30 and 8:30 Delaware time only; regenerates cumulative tables. Requires instructor approval for Tacoma.
- **Preview history:** `mode=test, task=history`. Saves three-column and enriched historical CSVs plus precipitation PNG as artifact `tacoma-history-preview`.
- **Store history:** `mode=collect, task=history`. Saves outputs to `data/tacoma/history/`. This may be triggered occasionally (e.g. day 20 and day 40), not every morning.

Once the city's selection and timezone are approved, point cron-job.org at:
`https://api.github.com/repos/yulinlin-0/CHEG807-weather/actions/workflows/collect_tacoma.yml/dispatches`
using `POST` and body `{"ref":"main","inputs":{"mode":"collect","task":"forecast"}}`. Keep GitHub fine-grained token secret in the cron-job.org Authorization header, never commit it. No native GitHub schedule is enabled for this Tacoma workflow.

## Official output structure

```text
data/tacoma/
  snapshots/YYYY-MM-DD.csv            # raw rolling 48-hour forecast snapshot
  plots/YYYY-MM-DD.png                # professor's precipitation probability plot
  day1_forecasts.csv                 # same local calendar day
  day2_forecasts.csv                 # next local calendar day
  day3_forecasts.csv                 # remaining portion of rolling 48-hour window, if any
  forecast_log_matlab_compatible.csv # professor's original four CSV columns, cumulative
  history/YYYY-MM-DD_to_YYYY-MM-DD_matlab_format.csv
  history/YYYY-MM-DD_to_YYYY-MM-DD_all_variables.csv
  history/YYYY-MM-DD_to_YYYY-MM-DD_precipitation.png
```

## Critical data provenance caveat

The professor's *Last 30 Days* code uses `https://api.open-meteo.com/v1/forecast` to query the **recent past**, not a verified independent surface-observation station feed. This implementation matches the teacher's code, but **do not assert these model-derived precipitation values are independent actual measured rain** without confirming the course accepts them. For the eventual probability-calibration analysis, consistent hourly periods and a justified rain/no-rain threshold are required. Open-Meteo may limit recent-past retention or refuse some 30-day historical queries; a failed call should be reported rather than fabricating data.

The GitHub Actions and API integration must be verified with a real test run; local code checks with mocked data do not verify live Open-Meteo accessibility.
