#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=Where an IP address is, from ip-api.com (no API key; its free tier is plain HTTP, so treat the answer as a hint, not a secret). Prints one line "City, Region, Country (CC) lat,lon tz" -- the City is the shape weather/current.py, weather/forecast.py and web/search.py take as their location. Pass ip= to look up a specific address; omitted, the caller's own public address is located.
#: when=Use when a workflow must find out where it is running (which city) before fetching local weather or news, or when the user asks where an IP address is.
#: network=required
#: stdin=none
#: param=ip:d=IPv4 or IPv6 address to locate; omitted, the caller's own public address
import json
import os
import sys
import urllib.parse
import urllib.request

ip = os.environ.get("IP", "").strip()
fields = "status,message,city,regionName,country,countryCode,lat,lon,timezone,query"
url = f"http://ip-api.com/json/{urllib.parse.quote(ip)}?fields={fields}"

try:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl"}), timeout=15) as resp:
        data = json.load(resp)
except Exception as e:
    print(f"geo-ip lookup failed: {e}", file=sys.stderr)
    sys.exit(1)

if data.get("status") != "success":
    print(f"geo-ip lookup failed for {data.get('query') or ip or 'own address'}: {data.get('message', 'no reason given')}", file=sys.stderr)
    sys.exit(1)

print(f"{data['city']}, {data['regionName']}, {data['country']} ({data['countryCode']}) {data['lat']},{data['lon']} {data['timezone']}")
