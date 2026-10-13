# CHEG 807 Project A: Weather Forecast Collection

This repository collects **weather forecast snapshots** for the CHEG 807 Project A assignment. It is not yet collecting independent actual-rain observations.

## Status

- Example city: Seattle, WA (for testing only; **not instructor approved**).
- Automated collection: **disabled** until approval (`COLLECT_ENABLED: "false"`).
- Manual tests: enabled; only generate downloadable test artifacts, never official daily data.

## Test now

1. Open **Actions** in this repository.
2. Select **CHEG807 Weather Forecast Collection**.
3. Click **Run workflow**, choose `main`, then **Run workflow**.
4. Wait for a green check. Open the workflow run and download the **forecast-test** artifact.
5. Inspect `forecast_test.csv`: collection timestamp, city, forecast timestamps, rain probabilities, temperature, forecast precipitation, humidity, wind speed, and weather code.

If GitHub shows an authorization or Actions-related prompt, enable Actions for this private repository.

## Start real collection (after instructor approval)

In `.github/workflows/collect_weather.yml`:

1. Replace `CITY_NAME`, `LATITUDE`, `LONGITUDE`, and `CITY_TIMEZONE` with the approved city.
2. Set `COLLECT_ENABLED: "true"`.
3. Commit the change on the default branch.

GitHub Actions attempts to run at **07:40 and 08:10 America/New_York** daily. Scheduled runs can be delayed or missed; the Python script only accepts completed fetches within **07:30–08:30** Delaware time and avoids saving duplicate daily snapshots. **Monitor Actions logs and snapshots**, especially during the first several days.

Official files appear under `data/snapshots/YYYY-MM-DD.csv`, with two cumulative tables in `data/day1_forecasts.csv` and `data/day2_forecasts.csv`.

## Data definition

- `day1`: target hours on the city's local calendar day of capture.
- `day2`: target hours on the city's next local calendar day.
- Captures the current rolling 48 hours, retaining applicable day1/day2 hours.
- API timestamps are requested as UTC Unix times to prevent ambiguity during daylight-saving shifts.
- `capture_time_ud` is the time of the API request, **not the original weather model issuance time**.
- Captures six meteorological quantities requested by the instructor's MATLAB forecast code, although that code saves only temperature and rain probability.
- Open-Meteo precipitation probability is for precipitation exceeding its stated hourly threshold; define observation criteria consistently with the instructor.

## Important limitations

- The forecast script does **not** collect actual hourly precipitation observations; those must be obtained and checked separately.
- GitHub scheduled runs can be late or dropped. Two triggers provide redundancy, not a timing guarantee.
- Use the instructor-approved location and source for official data; don't combine cities in one dataset.
- If your class requires each city's own 7:30–8:30 local time (rather than UD time), modify the schedule after clarifying with the instructor.
