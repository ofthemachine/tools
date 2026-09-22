#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Three-day weather forecast for a city, region, or landmark (Open-Meteo geocoding + forecast, no API key). Companion to weather/current.py, which only covers right now and takes the same location parameter. Pass day=0/1/2 to print just today, tomorrow, or day after; omitted prints all three days.
#: when=Use when the user asks about tomorrow's or the next few days' weather somewhere, or wants a planning-grade forecast rather than current conditions.
#: network=required
#: stdin=none
#: param=location:required:d=City, region, or landmark, e.g. Vancouver or Mount Fuji
#: param=day:d=0 today, 1 tomorrow, 2 day after; omit for all three
import json
import os
import sys
import urllib.parse
import urllib.request

WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm",
}


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


location = os.environ["LOCATION"]
geo_url = "https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + urllib.parse.quote(location)
try:
    with urllib.request.urlopen(geo_url, timeout=30) as resp:
        geo = json.load(resp)
except Exception as e:
    fail(f"geocoding request failed: {e}")

results = geo.get("results") or []
if not results:
    fail(f"no geocoding result for {location}")

lat = results[0]["latitude"]
lon = results[0]["longitude"]
label = results[0].get("name") or location
country = results[0].get("country_code") or ""

forecast_url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
    "&forecast_days=3&timezone=auto"
)
try:
    with urllib.request.urlopen(forecast_url, timeout=30) as resp:
        data = json.load(resp)
except Exception as e:
    fail(f"forecast request failed: {e}")

daily = data.get("daily") or {}
dates = daily.get("time") or []
codes = daily.get("weather_code") or []
highs = daily.get("temperature_2m_max") or []
lows = daily.get("temperature_2m_min") or []
precip = daily.get("precipitation_sum") or []
if not dates:
    fail("forecast response missing daily data")


def line(i):
    code = codes[i] if i < len(codes) else None
    hi = highs[i] if i < len(highs) else "?"
    lo = lows[i] if i < len(lows) else "?"
    rain = precip[i] if i < len(precip) else 0
    cond = WMO.get(code, "Unknown")
    return f"{dates[i]}: {cond}, high {hi}°C / low {lo}°C, precip {rain} mm"


day_raw = os.environ.get("DAY", "")
if day_raw != "":
    day = int(day_raw)
    if day not in (0, 1, 2) or day >= len(dates):
        fail(f"day must be 0 (today), 1 (tomorrow), or 2 (day after) -- got {day_raw}")
    print(f"{label}, {['today', 'tomorrow', 'day after'][day]}: {line(day)}")
else:
    print(f"Location: {label}, {country}")
    print("Weather Forecast:")
    for i in range(len(dates)):
        print(f"  {line(i)}")
