#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=A weather frog (Wetterfrosch): how nice one day will be somewhere, as a rung on its ladder from 0 (stay in) to 1 (glorious), plus a one-line croak saying why and whether to take an umbrella, and the chance of rain (rain.txt, 0 to 1) a body can drink from. Open-Meteo, no API key. The rung is a number a body can climb by; the croak is what it says.
#: when=Use when an agent's body or a morning card wants the forecast as one number and one line rather than a table.
#: network=required
#: stdin=none
#: param=location:required:d=City, region, or landmark, e.g. Toronto
#: param=day:default=1:kind=enum(0|1|2):d=0 today, 1 tomorrow, 2 the day after
#: output=rung.txt
#: output=croak.txt
#: output=rain.txt
import json
import os
import sys
import urllib.parse
import urllib.request

WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "showers", 81: "heavy showers", 82: "violent showers",
    95: "thunderstorms",
}
DAYS = ["Today", "Tomorrow", "The day after"]


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except Exception as e:
        fail(f"request failed: {e}")


location = os.environ["LOCATION"]
day = int(os.environ.get("DAY") or "1")
if day not in (0, 1, 2):
    fail(f"day must be 0, 1 or 2 -- got {day}")

geo = fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + urllib.parse.quote(location))
results = geo.get("results") or []
if not results:
    fail(f"no geocoding result for {location}")
place = results[0]
daily = fetch(
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={place['latitude']}&longitude={place['longitude']}"
    "&daily=weather_code,temperature_2m_max,precipitation_probability_max,wind_speed_10m_max"
    "&forecast_days=3&timezone=auto"
).get("daily") or {}


def at(key, default):
    vals = daily.get(key) or []
    return vals[day] if day < len(vals) and vals[day] is not None else default


code = at("weather_code", 3)
high = at("temperature_2m_max", 15)
rain = at("precipitation_probability_max", 0) / 100
wind = at("wind_speed_10m_max", 10)

# The rung: start at the top, lose height for rain, gloom, wind, and a day
# too cold or too hot to enjoy. Deliberately simple: a frog, not a model.
rung = 1.0
rung -= 0.55 * rain
rung -= {0: 0, 1: 0, 2: 0.05, 3: 0.15, 45: 0.2, 48: 0.2}.get(code, 0.3 if code < 95 else 0.45)
rung -= min(0.2, max(0, wind - 25) / 100)
rung -= min(0.3, abs(high - 21) / 40)
rung = round(max(0.0, min(1.0, rung)), 2)

umbrella = rain >= 0.5 or code in (61, 63, 65, 80, 81, 82, 95)
verdict = "Umbrella." if umbrella else "Leave the umbrella." if rung >= 0.6 else "Bring a jacket."
croak = f"Ribbit. {DAYS[day]} in {place.get('name') or location}: {WMO.get(code, 'weather')}, {round(high)}°C, {round(rain * 100)}% rain. {verdict}"

os.makedirs("/output", exist_ok=True)
with open("/output/rung.txt", "w") as f:
    f.write(f"{rung}\n")
with open("/output/croak.txt", "w") as f:
    f.write(croak + "\n")
with open("/output/rain.txt", "w") as f:  # the chance of rain, 0 to 1: a need a body can drink from
    f.write(f"{round(rain, 2)}\n")
print(f"rung {rung}: {croak}")
