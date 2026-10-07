#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=The latest headlines from a news feed (RSS or Atom), newest first. Clean markdown list by default, or TSV when format=tsv.
#: when=Use when the user wants today's top news or the latest headlines from an outlet, section, or feed, or a briefing, caption, or prompt needs a live headline.
#: network=required
#: stdin=none
#: param=feed:default=feeds.bbci.co.uk/news/world/rss.xml:d=RSS or Atom feed URL (https:// is assumed when no scheme is given)
#: param=count:default=5:d=How many headlines to print
#: param=format:default=markdown:d=Output format: "markdown" for formatted clickable links, or "tsv" for title\tlink\tdate
import email.utils
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ATOM = "{http://www.w3.org/2005/Atom}"
feed = os.environ.get("FEED", "feeds.bbci.co.uk/news/world/rss.xml").strip()
if "://" not in feed:
    feed = "https://" + feed

try:
    count = int(os.environ.get("COUNT", "5"))
except ValueError:
    count = 5

fmt = os.environ.get("FORMAT", "markdown").strip().lower()

req = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read())
except (urllib.error.URLError, ET.ParseError) as e:
    print(f"feed fetch failed: {e}", file=sys.stderr)
    sys.exit(1)


def text(el, tag):
    found = el.find(tag)
    return found.text.strip() if found is not None and found.text else ""


def clean_url(u):
    if not u:
        return ""
    parsed = urllib.parse.urlparse(u)
    q = urllib.parse.parse_qsl(parsed.query)
    clean_q = [(k, v) for k, v in q if not (k.startswith("utm_") or k.startswith("at_") or k in ("ocid",))]
    new_q = urllib.parse.urlencode(clean_q)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))


def clean_date(d_str):
    if not d_str:
        return ""
    try:
        dt = email.utils.parsedate_to_datetime(d_str)
    except Exception:
        try:
            dt = datetime.fromisoformat(d_str.replace("Z", "+00:00"))
        except Exception:
            return d_str[:16]
    now = datetime.now(timezone.utc)
    diff = now - dt.astimezone(timezone.utc)
    secs = int(diff.total_seconds())
    if 0 <= secs < 3600:
        mins = max(1, secs // 60)
        return f"{mins}m ago"
    elif 0 <= secs < 86400:
        hrs = secs // 3600
        return f"{hrs}h ago"
    elif 0 <= secs < 86400 * 7:
        days = secs // 86400
        return f"{days}d ago"
    return dt.strftime("%b %d")


channel_title = ""
ch = root.find(".//channel/title")
if ch is None:
    ch = root.find(f"{ATOM}title")
if ch is not None and ch.text:
    channel_title = ch.text.strip()

raw_items = []
for item in root.findall(".//item"):  # RSS
    raw_items.append((text(item, "title"), text(item, "link"), text(item, "pubDate")))
for entry in root.findall(f".//{ATOM}entry"):  # Atom
    link_el = entry.find(f"{ATOM}link")
    link_href = link_el.get("href", "") if link_el is not None else ""
    raw_items.append((text(entry, f"{ATOM}title"), link_href, text(entry, f"{ATOM}updated") or text(entry, f"{ATOM}published")))

rows = []
for t, l, raw_d in raw_items:
    if t and l:
        rows.append((t, clean_url(l), clean_date(raw_d), raw_d))
    if len(rows) >= count:
        break

if not rows:
    print("no headlines found", file=sys.stderr)
    sys.exit(1)

if fmt == "tsv":
    for t, l, _, raw_d in rows:
        print(f"{t}\t{l}\t{raw_d}")
    sys.exit(0)

# Markdown format
lines = []
if channel_title:
    lines.append(f"📰 **{channel_title}**")
    lines.append("")

for idx, (t, l, d, _) in enumerate(rows, 1):
    suffix = f" — {d}" if d else ""
    if count == 1:
        lines.append(f"[{t}]({l}){suffix}")
    else:
        lines.append(f"{idx}. [{t}]({l}){suffix}")

print("\n".join(lines))
