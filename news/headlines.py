#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=The latest headlines from a news feed (RSS or Atom), newest first, one "title<TAB>link<TAB>date" line each; BBC world news unless another feed is named. count=1 gives the single top story.
#: when=Use when the user wants today's top news or the latest headlines from an outlet, section, or feed, or a briefing, caption, or prompt needs a live headline.
#: network=required
#: stdin=none
#: param=feed:default=feeds.bbci.co.uk/news/world/rss.xml:d=RSS or Atom feed URL (https:// is assumed when no scheme is given)
#: param=count:default=5:d=How many headlines to print
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
feed = os.environ["FEED"].strip()
if "://" not in feed:
    feed = "https://" + feed
count = int(os.environ["COUNT"])

req = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())
except (urllib.error.URLError, ET.ParseError) as e:
    print(f"feed fetch failed: {e}", file=sys.stderr)
    sys.exit(1)


def text(el, tag):
    found = el.find(tag)
    return found.text.strip() if found is not None and found.text else ""


rows = []
for item in root.findall(".//item"):  # RSS
    rows.append((text(item, "title"), text(item, "link"), text(item, "pubDate")))
for entry in root.findall(f".//{ATOM}entry"):  # Atom
    link = entry.find(f"{ATOM}link")
    rows.append((text(entry, f"{ATOM}title"), link.get("href", "") if link is not None else "",
                 text(entry, f"{ATOM}updated") or text(entry, f"{ATOM}published")))

rows = [r for r in rows if r[0] and r[1]][:count]
if not rows:
    print("no headlines found", file=sys.stderr)
    sys.exit(1)
for title, link, date in rows:
    print(f"{title}\t{link}\t{date}")
