#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=The Moon's phase on a given UTC date, computed with ephem (no network): phase name, percent illuminated, and the dates of the next new and full moon. One line, ready for a dateline or an almanac box. The date is a parameter, never the clock, so the same inputs always give the same answer.
#: when=Use when the user asks what phase the moon is in or when the next full or new moon is, or an almanac, dateline, or caption needs the moon for a specific date.
#: network=none
#: stdin=none
#: param=date:required:d=UTC date as YYYY-MM-DD
import os
import sys

import ephem

date = os.environ["DATE"].strip()
try:
    d = ephem.Date(date.replace("-", "/"))
except (ValueError, TypeError) as e:
    print(f"bad date {date!r}: use YYYY-MM-DD ({e})", file=sys.stderr)
    sys.exit(2)

moon = ephem.Moon(d)
illum = moon.phase  # percent of the disc illuminated
prev_new = ephem.previous_new_moon(d)
next_new = ephem.next_new_moon(d)
next_full = ephem.next_full_moon(d)
age = d - prev_new  # days since new moon
cycle = next_new - prev_new
frac = age / cycle

if frac < 0.03 or frac > 0.97:
    name = "New Moon"
elif frac < 0.22:
    name = "Waxing Crescent"
elif frac < 0.28:
    name = "First Quarter"
elif frac < 0.47:
    name = "Waxing Gibbous"
elif frac < 0.53:
    name = "Full Moon"
elif frac < 0.72:
    name = "Waning Gibbous"
elif frac < 0.78:
    name = "Last Quarter"
else:
    name = "Waning Crescent"

fmt = lambda e: ephem.Date(e).datetime().strftime("%Y-%m-%d")
print(f"{name}, {illum:.0f}% illuminated, day {age:.0f} of the cycle; next full moon {fmt(next_full)}, next new moon {fmt(next_new)}")
