collect_forecast("Newark, DE", 51.50722, -0.12750, "20261012_newark_next2.csv")


function F = collect_forecast(city, latitude, longitude, saveDir)
% Save the hourly forecast for the next 48 hours. Each run is appended to
% one CSV file so multiple runs will be added to the same CSV file without
% overwriting. Ensure file is not currently open for the append to work.
%
% Run at the same time every day for the next 30 days. There is a way to
% have your Mac or Windows system to run this file at a set time each day.
% If you would like, that is an easier option that you can pursue.

    arguments
        city (1,1) string
        latitude  (1,1) double {mustBeBetween(latitude, -90, 90)}
        longitude (1,1) double {mustBeBetween(longitude, -180, 180)}
        saveDir (1,1) string = ""
    end

    opts = weboptions('Timeout', 30);

    %convert city name to coordinates in latitude and longtitude
    webResults = struct( ...
    "name",      city, ...
    "country",   "United States", ...
    "latitude",  latitude, ...
    "longitude", longitude, ...
    "timezone",  "America/New_York");

    fprintf("%s, %s (%.3f, %.3f)\n\n", webResults.name, webResults.country, ...
        webResults.latitude, webResults.longitude);

    %fetch forecast for next 48 hours from time of running this script
    vars = ["temperature_2m", "precipitation_probability", "precipitation", ...
            "relative_humidity_2m", "wind_speed_10m", "weather_code"];

    data = webread("https://api.open-meteo.com/v1/forecast", ...
        "latitude",      webResults.latitude, ...
        "longitude",     webResults.longitude, ...
        "forecast_days", 3, ...
        "hourly",        strjoin(vars, ","), ...
        "timezone",      webResults.timezone, opts);
    h = data.hourly;

    tz= string(webResults.timezone);
    times = datetime(h.time, "InputFormat", "yyyy-MM-dd'T'HH:mm", "TimeZone", tz);
    nowLocal = dateshift(datetime("now", "TimeZone", tz), "start", "hour");
    keep  = times >= nowLocal & times < nowLocal + hours(48);

    currTime = repmat(datetime("now", "TimeZone", tz), nnz(keep), 1);

    F = table(currTime, times(keep), ...
        h.temperature_2m(keep), h.precipitation_probability(keep), ... ...
        'VariableNames', ["currTime", "ForecastTime", "Temp_C", ...
                          "RainChance_pct"]);
    F.currTime.Format    = "yyyy-MM-dd HH:mm";
    F.ForecastTime.Format = "yyyy-MM-dd HH:mm";

    %APPEND to saveDir file
    if saveDir == ""
        saveDir = lower(strrep(string(webResults.name), " ", "_")) + "_forecast_log.csv";
    end
    isNew = ~isfile(saveDir);
    writetable(F, saveDir, "WriteMode", "append", "WriteVariableNames", isNew);

    fprintf("%s: saved %d forecast hours for %s to %s\n", ...
            string(datetime("now"), "yyyy-MM-dd HH:mm"), height(F), webResults.name, saveDir);

    %quick check to ensure data looks correct
    figure;
    plot(F.ForecastTime, F.RainChance_pct);
    grid on;
    title("Hourly precipitation against day");
    ylabel("% Likelihood of rain");
end

