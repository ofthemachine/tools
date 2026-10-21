#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:59784cff1945b7d6093a591b5e5292b8c989f0691af0494fbbe1c6b8083a16cb
#: d=How light it is outside right now at a latitude and longitude, as one number from 0 (night) to 1 (the sun overhead): the sine of the sun's altitude, computed with ephem (no network). A body can grow by it.
#: when=Use when an agent's body or a card wants daylight now as a single number, e.g. a plant that opens in the sun.
#: network=none
#: stdin=none
#: param=lat:required:d=Latitude in decimal degrees, e.g. 43.65
#: param=lon:required:d=Longitude in decimal degrees, east positive, e.g. -79.38
#: output=light.txt
import math
import os
import sys

import ephem

try:
    lat, lon = float(os.environ["LAT"]), float(os.environ["LON"])
except (KeyError, ValueError):
    sys.exit("daylight: lat and lon are decimal degrees")

here = ephem.Observer()
here.lat, here.lon = str(lat), str(lon)
sun = ephem.Sun(here)
alt = math.degrees(float(sun.alt))
light = round(max(0.0, math.sin(math.radians(alt))), 2)

os.makedirs("/output", exist_ok=True)
with open("/output/light.txt", "w") as f:
    f.write(f"{light}\n")
print(f"light {light}: the sun is {alt:.0f}° {'up' if alt >= 0 else 'down'}")
