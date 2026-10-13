T = weather_30_days("Newark", 39.6837, -75.7497, "20261012_newark_past30.csv", 30);

function T = weather_30_days(city, latitude, longitude, saveDir, nDays)
% Get hourly weather for the past N days for your chosen city.
%
%   Uses the Open-Meteo APIs (no key needed). Open-Meteo gets predictions
%   from over 15 international and national weather services, notably NOAA
%   / NCEP in the US.
%

arguments
    city (1,1) string
    latitude  (1,1) double {mustBeBetween(latitude, -90, 90)}
    longitude (1,1) double {mustBeBetween(longitude, -180, 180)}
    saveDir (1,1) string = ""
    nDays (1,1) double = 30
end

opts = weboptions('Timeout', 15);

%convert city name to coordinates in latitude and longtitude
%change timezone if needed!
webResults = struct( ...
    "name",      city, ...
    "country",   "United States", ...
    "latitude",  latitude, ...
    "longitude", longitude, ...
    "timezone",  "America/New_York");


%!!!! If webread fails to find coordinates, you can enter the city name and
%county and latitude and longitude manually into the variable r above!!!
fprintf("%s, %s (%.3f, %.3f)\n\n", webResults.name, webResults.country, ...
    webResults.latitude, webResults.longitude);

%collect hourly data
endDate   = datetime("today") - days(1);
startDate = endDate - days(nDays - 1);

hourlyVars = ["temperature_2m", "relative_humidity_2m", ...
    "precipitation", "wind_speed_10m", "weather_code"];

data = webread("https://api.open-meteo.com/v1/forecast", ...
    "latitude",   webResults.latitude, ...
    "longitude",  webResults.longitude, ...
    "start_date", string(startDate, "yyyy-MM-dd"), ...
    "end_date",   string(endDate,   "yyyy-MM-dd"), ...
    "hourly",     strjoin(hourlyVars, ","), ...
    "timezone",   webResults.timezone, opts);

h = data.hourly;

%tabulate data. feel free to change and remove variables
T = table( ...
    datetime(h.time, "InputFormat", "yyyy-MM-dd'T'HH:mm"), ...
    h.temperature_2m, h.precipitation, ...
    'VariableNames', ["Time", "Temp_C", "Precip_mm"]);

disp(head(T, 20));

%output to CSV file
if saveDir == ""
    saveDir = lower(strrep(webResults.name, " ", "_")) + "_hourly.csv";
end
writetable(T, saveDir);
fprintf("Saved to %s\n", saveDir);

%quick check to ensure data looks correct
figure;
plot(T.Time, T.Precip_mm);
grid on;
title("Hourly precipitation against day");
ylabel("mm");
end