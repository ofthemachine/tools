#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=Top N headlines (title + story link + pubDate) from any public RSS feed -- generalizes world-headline.py's single BBC-world-only fetch to an arbitrary feed URL, so a caller can mix categories/outlets for tonal variety instead of always getting the same section.
#: when=Use when the user names a feed, outlet, or topic section and wants its latest headlines, or a briefing needs sources beyond BBC world news.
#: network=required
#: stdin=none
#: param=feed:required:d=Public RSS/Atom feed URL
#: param=count:default=5:d=Number of headlines to print
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

feed = os.environ.get("FEED", "").strip()
count = int(os.environ["COUNT"])

if not feed:
    print("rss-headlines: missing feed", file=sys.stderr)
    sys.exit(1)

req = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
except urllib.error.URLError as e:
    print(f"feed fetch failed: {e}", file=sys.stderr)
    sys.exit(1)

items = ET.fromstring(data).findall(".//item")[:count]
if not items:
    print("no headlines found", file=sys.stderr)
    sys.exit(1)

for item in items:
    title = item.find("title")
    link = item.find("link")
    pub = item.find("pubDate")
    if title is None or link is None:
        continue
    pub_text = pub.text.strip() if pub is not None and pub.text else ""
    print(f"{title.text.strip()}\t{link.text.strip()}\t{pub_text}")
