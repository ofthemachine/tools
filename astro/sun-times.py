#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Sunrise, sunset, and day length for a latitude, longitude, and UTC date, computed with ephem (no network). Times are printed in the given UTC offset so a caller can pass the local zone; the day-length delta against the day before says whether days are getting longer or shorter. Companion to net/geo-ip.py, whose lat,lon this takes.
#: when=Use when the user asks when the sun rises or sets somewhere, how long the day is, or an almanac or weather box needs sun times for a place and date.
#: network=none
#: stdin=none
#: param=lat:required:d=Latitude in decimal degrees, e.g. 53.5457
#: param=lon:required:d=Longitude in decimal degrees, east positive, e.g. -113.5
#: param=date:required:d=UTC date as YYYY-MM-DD
#: param=utc_offset:default=0:d=Hours to add when printing times, e.g. -6 for Edmonton in September
import datetime as dt
import os
import sys

import ephem

try:
    lat = float(os.environ["LAT"])
    lon = float(os.environ["LON"])
    offset = float(os.environ["UTC_OFFSET"])
    date = dt.date.fromisoformat(os.environ["DATE"].strip())
except ValueError as e:
    print(f"bad parameter: {e}", file=sys.stderr)
    sys.exit(2)


def day(d):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.date = ephem.Date(dt.datetime(d.year, d.month, d.day))
    sun = ephem.Sun()
    try:
        rise = obs.next_rising(sun).datetime()
        sets = obs.next_setting(sun).datetime()
    except (ephem.AlwaysUpError, ephem.NeverUpError) as e:
        return None, None, e
    return rise, sets, None


rise, sets, err = day(date)
if err:
    print(f"{date}: {'sun never sets' if isinstance(err, ephem.AlwaysUpError) else 'sun never rises'} at {lat},{lon}")
    sys.exit(0)
length = sets - rise if sets > rise else (sets + dt.timedelta(days=1)) - rise
prev_rise, prev_set, perr = day(date - dt.timedelta(days=1))
delta = ""
if not perr:
    plen = prev_set - prev_rise if prev_set > prev_rise else (prev_set + dt.timedelta(days=1)) - prev_rise
    diff = (length - plen).total_seconds()
    delta = f", {abs(diff) / 60:.1f} min {'longer' if diff > 0 else 'shorter'} than yesterday"

local = lambda t: (t + dt.timedelta(hours=offset)).strftime("%H:%M")
h, m = divmod(int(length.total_seconds() // 60), 60)
sign = "+" if offset >= 0 else "-"
print(f"sunrise {local(rise)}, sunset {local(sets)} (UTC{sign}{abs(offset):g}), day length {h}h {m:02d}m{delta}")
