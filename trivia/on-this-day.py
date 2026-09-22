#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Notable events that happened on a month and day in history, from Wikipedia's "On this day" feed (Wikimedia API, no key). One "YEAR<TAB>text" line per event, most recent first, count-limited, so a briefing can pick the one that rhymes with today.
#: when=Use when the user asks what happened on this day in history, or a newspaper, briefing, or caption wants an anniversary for a given date.
#: network=required
#: stdin=none
#: param=month:required:d=Month as a number, 1-12
#: param=day:required:d=Day of the month, 1-31
#: param=count:default=8:d=How many events to print
import json
import os
import sys
import urllib.request

try:
    month, day, count = int(os.environ["MONTH"]), int(os.environ["DAY"]), int(os.environ["COUNT"])
except ValueError as e:
    print(f"bad parameter: {e}", file=sys.stderr)
    sys.exit(2)

url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/{month:02d}/{day:02d}"
req = urllib.request.Request(url, headers={"User-Agent": "ofthemachine-tools (https://github.com/ofthemachine/tools)"})
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        events = json.load(resp).get("events") or []
except Exception as e:
    print(f"on-this-day request failed: {e}", file=sys.stderr)
    sys.exit(1)

events.sort(key=lambda ev: ev.get("year", 0), reverse=True)
for ev in events[:count]:
    print(f"{ev.get('year', '?')}\t{ev.get('text', '').strip()}")
