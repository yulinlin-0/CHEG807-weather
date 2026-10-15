# CHEG 807 Project A — Tacoma Weather Collection

**Project:** Collect fixed-time, hourly rainfall-probability forecasts for Tacoma, Washington, then evaluate probability calibration and information content after sufficient days. Forecast collection is working: the repository already contains a Tacoma snapshot and PNG chart from **2026-10-15 at 07:30:27 America/New_York** (04:30:27 Tacoma local time).

This is a **weather-data acquisition project**, not a Python weather prediction model. The numerical forecasts come from the **Open-Meteo Forecast API**; the Python programs request, timestamp, save and plot that data. No MATLAB installation or personal computer running overnight is required.

## 1. City, schedule and data source

| Setting | Value |
| --- | --- |
| City | Tacoma, WA |
| Latitude / longitude | 47.2529, -122.4443 |
| Weather location timezone | America/Los_Angeles |
| Collection schedule timezone | **America/New_York** (Delaware/UD time) |
| External scheduler | **cron-job.org at 07:30 Eastern daily** |
| Forecast provider | Open-Meteo Forecast API |
| Repository branch | main |
| Workflow | [CHEG807 Tacoma Forecast and Historical Weather](.github/workflows/collect_tacoma.yml) |

**Time-zone clarification:** 07:30 Delaware time is 04:30 in Tacoma. This is the schedule currently configured and verified, *not* 07:30 Tacoma local time. If the instructor intends city-local 07:30–08:30, update **both** the cron-job.org schedule and the Python collection-window guard in \`collect_tacoma.py\`. Tacoma selection and collection-time interpretation should be confirmed with the instructor before treating the data as graded observations.

GitHub Actions **does not use its own cron schedule** for this project. An external request triggers the workflow; a late Actions run will be rejected by the Python time-window check rather than falsely counted as an on-time forecast.

## 2. Programs — both original MATLAB functions are reproduced

| Instructor file | Python file | What it does |
| --- | --- | --- |
| \`Grab Weather Data Next 2 Days.m\` | [collect_tacoma.py](collect_tacoma.py) | Retrieve rolling **48 hourly forecasts** from the current hour; save timestamped CSVs and an hourly rain-probability line plot; accumulate the instructor's four-column output |
| \`Grab Weather Data Last 30 Days.m\` | [collect_tacoma_history.py](collect_tacoma_history.py) | Retrieve hourly weather records for the **past 30 local calendar days through yesterday**; print the first 20 rows; write the instructor's three-column output, an all-variable CSV, and a precipitation plot |

Both Python scripts use the same Open-Meteo **/v1/forecast** endpoint requested by the original MATLAB scripts. They also preserve all queried weather variables instead of discarding them.

**48-hour forecast variables:** \`temperature_2m\`, \`precipitation_probability\`, \`precipitation\`, \`relative_humidity_2m\`, \`wind_speed_10m\`, \`weather_code\`.

**30-day history variables:** \`temperature_2m\`, \`relative_humidity_2m\`, \`precipitation\`, \`wind_speed_10m\`, \`weather_code\`.

The unchanged instructor-provided \`.m\` scripts remain under [professor_matlab/original/](professor_matlab/original/) for comparison. **Do not run the original forecast file without correcting its coordinates:** its displayed "Newark, DE" label is paired with London coordinates.

## 3. Automatic forecast collection

At 07:30 Eastern, cron-job.org makes a POST request to:

\`\`\`text
https://api.github.com/repos/yulinlin-0/CHEG807-weather/actions/workflows/collect_tacoma.yml/dispatches
\`\`\`

Use:

- **Timezone / recurrence:** \`America/New_York\`, every day at \`07:30\`
- **Request method:** \`POST\`
- **Request body:**
  \`\`\`json
  {"ref":"main","inputs":{"mode":"collect","task":"forecast"}}
  \`\`\`
- **Headers:** \`Authorization: Bearer <your GitHub fine-grained token>\`, \`Accept: application/vnd.github+json\`, \`Content-Type: application/json\`

Keep the token **secret**, only in cron-job.org's HTTP header settings, and do not commit it to this public repository. The token should have the minimum repository Actions write permission required and must be renewed when it expires.

\`mode=collect\` saves one forecast snapshot per Delaware calendar day **only when the API collection begins and finishes between 07:30 and 08:30 Eastern**. If GitHub starts late, or that day's original snapshot already exists, it does not replace the original daily record. A successful HTTP 204 means GitHub accepted the dispatch; **also check the Actions run and committed files** to confirm the forecast was collected.

The historical 30-day script is **not run daily**; it can be triggered separately (e.g. near day 20 and day 40).

## 4. Where the data and figures are stored

\`\`\`text
data/tacoma/
├── snapshots/
│   ├── 2026-10-15.csv                 # complete rolling 48-hour capture
│   └── YYYY-MM-DD.csv                 # one new file for each successful day
├── plots/
│   ├── 2026-10-15.png                 # forecast probability vs local forecast time
│   └── YYYY-MM-DD.png
├── day1_forecasts.csv                 # same Tacoma calendar day as capture
├── day2_forecasts.csv                 # next Tacoma calendar day
├── day3_forecasts.csv                 # remaining hours in the rolling 48-h window
├── forecast_log_matlab_compatible.csv # all 48-h records, instructor's 4 columns
└── history/                            # created when history is collected
    ├── YYYY-MM-DD_to_YYYY-MM-DD_matlab_format.csv
    ├── YYYY-MM-DD_to_YYYY-MM-DD_all_variables.csv
    └── YYYY-MM-DD_to_YYYY-MM-DD_precipitation.png
\`\`\`

**Snapshots versus day spreadsheets:** each \`snapshots/YYYY-MM-DD.csv\` preserves the full original 48-hour forecast from **one acquisition**. The three \`dayN_forecasts.csv\` files are regenerated from **all saved snapshots** each day. Their old rows remain included; they are not reduced to today's records. Day 1/2/3 are **relative to each capture's Tacoma local calendar date**, not the project's first, second and third days.

At approximately 04:30 Tacoma time on a non-DST-transition day, a 48-hour snapshot contains **20 same-day hours, 24 next-day hours, and 4 third-calendar-day hours**. The assignment focuses on the Day 1 vs Day 2 comparison; Day 3 is stored to avoid discarding API results.

### CSV fields

The full forecast CSV includes:

- \`capture_time_utc\`: exact API request time in UTC
- \`capture_time_ud\`: that same instant in Delaware local time
- \`capture_time_city\`: that same instant in **Tacoma local time**
- \`forecast_time_utc\` and \`forecast_time_city\`: the hour being predicted
- \`forecast_day\`, \`hours_ahead_from_current_hour\`
- \`rain_chance_pct\`, \`temperature_c\`, \`forecast_precip_mm\`, \`relative_humidity_pct\`, \`wind_speed_kmh\`, \`weather_code\`
- \`city\`, \`latitude\`, \`longitude\`, \`city_timezone\`, \`source\`

**MATLAB-compatible forecast table:** \`currTime\`, \`ForecastTime\`, \`Temp_C\`, \`RainChance_pct\` (combines all snapshots, rather than using a fragile direct append).

**MATLAB-compatible past-weather table:** \`Time\`, \`Temp_C\`, \`Precip_mm\`. The extra historical CSV also preserves all five queried variables, UTC times, an indicator for precipitation > 0 mm, and provenance.

## 5. How to run and test the two programs

Open [GitHub Actions → CHEG807 Tacoma Forecast and Historical Weather](https://github.com/yulinlin-0/CHEG807-weather/actions/workflows/collect_tacoma.yml), choose **Run workflow** and select:

| Mode | Task | Result |
| --- | --- | --- |
| \`test\` | \`forecast\` | CSVs + PNG in downloadable \`tacoma-forecast-preview\` **Artifact**; nothing written into official data |
| \`test\` | \`history\` | Past-weather CSVs + PNG in \`tacoma-history-preview\` **Artifact**; no official changes |
| \`collect\` | \`forecast\` | Official CSVs + PNG committed under \`data/tacoma/\`; **7:30–8:30 Eastern only** |
| \`collect\` | \`history\` | Historical CSVs + PNG committed under \`data/tacoma/history/\`; can run outside the daily collection window |

Artifacts are found on an individual successful workflow-run page under **Artifacts**. Daily official CSV/PNG are found in the repository itself, **not** in Artifacts.

The current requirements are in [requirements-tacoma.txt](requirements-tacoma.txt) (Matplotlib for PNG output).

## 6. Accuracy, provenance and assignment limitations

1. The Forecast API gives **forecast-model outputs**, not predictions computed by these Python scripts.
2. The professor's "Last 30 Days" MATLAB code also queries the **Forecast API** for past precipitation. This Python port intentionally matches that behavior, but those values are **not guaranteed independent rain-gauge observations**. Independently sourced observed precipitation, or the instructor's confirmation that Open-Meteo model-derived recent past is acceptable, is needed for defensible validation.
3. The **actual rain/no-rain** evaluation, probability bin calibration, and Shannon information / negentropy analysis are later analysis steps and are **not yet implemented**.
4. Keep both the forecast **capture timestamp** and the **forecast target-hour timestamp**. Only compare forecast probability to an observed precipitation event for the *matching hour*.
5. This public repository contains no GitHub token or private credential. Previous Seattle scheduling experiments were removed from the current branch; original MATLAB code is preserved for academic traceability.

## Official current files

- [Daily forecasts (raw snapshots)](data/tacoma/snapshots/)
- [Daily probability figures](data/tacoma/plots/)
- [Day 1 forecasts](data/tacoma/day1_forecasts.csv)
- [Day 2 forecasts](data/tacoma/day2_forecasts.csv)
- [Day 3 forecast tail](data/tacoma/day3_forecasts.csv)
- [Original four-column forecast format](data/tacoma/forecast_log_matlab_compatible.csv)
