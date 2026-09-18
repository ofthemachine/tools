#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=Today's top N world-news headlines (title + story link) from BBC's public RSS feed, one "title\tlink" pair per line -- same feed/image as world-headline.py, extended with the link and a count so a caller can build several memes instead of just one.
#: when=Use when the user wants several of today's top world headlines with links, or a briefing needs a world-news section.
#: network=required
#: stdin=none
#: param=count:default=5:d=Number of headlines to print
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

count = int(os.environ["COUNT"])

url = "https://feeds.bbci.co.uk/news/world/rss.xml"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
except urllib.error.URLError as e:
    print(f"headlines fetch failed: {e}", file=sys.stderr)
    sys.exit(1)

items = ET.fromstring(data).findall(".//item")[:count]
if not items:
    print("no headlines found", file=sys.stderr)
    sys.exit(1)

for item in items:
    title = item.find("title")
    link = item.find("link")
    if title is None or link is None:
        continue
    print(f"{title.text.strip()}\t{link.text.strip()}")
