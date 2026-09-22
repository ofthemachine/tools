#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Today's top world-news headline from BBC's public RSS feed -- no API key needed, same "stdlib only, real live data" taste as weather/current.py.
#: when=Use when the user asks for today's top world news story, or one live headline is needed as a prompt or caption.
#: network=required
#: stdin=none
import sys
import urllib.request
import xml.etree.ElementTree as ET

url = "https://feeds.bbci.co.uk/news/world/rss.xml"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
except urllib.error.URLError as e:
    print(f"headline fetch failed: {e}", file=sys.stderr)
    sys.exit(1)

item = ET.fromstring(data).find(".//item")
if item is None or item.find("title") is None:
    print("no headlines found", file=sys.stderr)
    sys.exit(1)

print(item.find("title").text.strip())
