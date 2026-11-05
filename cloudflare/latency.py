#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=How fast a Cloudflare site's origin answers, path by path: requests, p50/p95/p99 and size over the last 24 hours, against the last hour and the 24 hours before, flagging a real slowdown. An address making most of a window's requests is left out of it and named, so a flood cannot skew the numbers. Long polls are labelled and never flagged: their time is waiting. Read-only.
#: when=Use when someone asks how fast a Cloudflare site is answering, which path is slow, or whether a change made it faster or slower; for how much traffic and from whom, use cloudflare/traffic.
#: network=required
#: stdin=none
#: secret=CLOUDFLARE_API_TOKEN:d=A Cloudflare API token with Zone Analytics read and Zone read (read-only)
#: param=zone:required:d=The zone (domain) to read, e.g. example.com
#: param=longpoll:default=:d=Comma-separated paths that wait for news by design, e.g. /v1/since
#: param=top:default=12:d=How many paths to list
#: output=report.md
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.cloudflare.com/client/v4"
TEMPFAIL = 75  # a rate limit, a 5xx or a dropped connection may pass: fragletc --retry

# When a slowdown is real: p95 at least this many times the day before, by at
# least this much, on enough requests for a p95 to mean anything.
SLOW_FACTOR, SLOW_BY_MS, MIN_REQUESTS = 2, 100, 20
FLOOD_SHARE, FLOOD_MIN = 0.5, 100  # one address, of a window's requests
HASH = re.compile(r"/[0-9a-f]{64}\b")

# A Worker's fetch is where origin timing lives; a client's own request to a
# Worker reads as 0 ms, a perfect and meaningless number.
SOURCE = 'requestSource:"edgeWorkerFetch"'
TIMES = "quantiles{originResponseDurationMsP50 originResponseDurationMsP95 originResponseDurationMsP99} sum{edgeResponseBytes}"


def fail(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


token = open(os.environ["CLOUDFLARE_API_TOKEN_FILE"], encoding="utf-8").read().strip()


def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.load(resp)
    except urllib.error.HTTPError as e:
        fail(f"Cloudflare returned HTTP {e.code} for {path}", TEMPFAIL if e.code == 429 or e.code >= 500 else 1)
    except (urllib.error.URLError, TimeoutError) as e:
        fail(f"Cloudflare request failed: {e}", TEMPFAIL)
    if res.get("errors"):
        fail(f"Cloudflare: {res['errors']}")
    return res


zone = os.environ["ZONE"].strip().lower()
top = int(os.environ["TOP"])
longpoll = {p.strip() for p in os.environ.get("LONGPOLL", "").split(",") if p.strip()}
zones = call("/zones?name=" + urllib.parse.quote(zone))["result"]
if not zones:
    fail(f"no zone {zone} that this token can read")
zone_id = zones[0]["id"]


def groups(start, end, filters, fields, limit=5000):
    """A window's request groups, under the given filters."""
    q = ("query($z:String!,$s:Time!,$e:Time!){viewer{zones(filter:{zoneTag:$z}){"
         f"g:httpRequestsAdaptiveGroups(limit:{limit},orderBy:[count_DESC],filter:{{datetime_geq:$s,datetime_lt:$e,{SOURCE}{filters}}}){{count {fields}}}"
         "}}}")
    iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return call("/graphql", {"query": q, "variables": {"z": zone_id, "s": iso(start), "e": iso(end)}})["data"]["viewer"]["zones"][0]["g"]


def row(g):
    q = g["quantiles"]
    return {"n": g["count"], "p50": q["originResponseDurationMsP50"], "p95": q["originResponseDurationMsP95"],
            "p99": q["originResponseDurationMsP99"], "bytes": g["sum"]["edgeResponseBytes"]}


def window(start, end):
    """Each path's timing in a window, and the address left out of it, if any.

    Percentiles of separate groups cannot be merged, so a path with a hash in it
    (every blob its own) is read again as one group, by its prefix."""
    addresses = groups(start, end, "", "dimensions{clientIP}", 100)
    total = sum(a["count"] for a in addresses)
    flood, skip = None, ""
    if addresses and total >= FLOOD_MIN and addresses[0]["count"] / total > FLOOD_SHARE:
        flood = (addresses[0]["dimensions"]["clientIP"], addresses[0]["count"] / total)
        skip = f',clientIP_neq:"{flood[0]}"'
    paths, prefixes = {}, set()
    for g in groups(start, end, skip, f"dimensions{{clientRequestPath}} {TIMES}"):
        path = g["dimensions"]["clientRequestPath"]
        if HASH.search(path):
            prefixes.add(path[:HASH.search(path).start()] + "/")
        else:
            paths[path] = row(g)
    for prefix in prefixes:
        whole = groups(start, end, f'{skip},clientRequestPath_like:"{prefix}%"', TIMES, 1)
        if whole:
            paths[prefix + "<hash>"] = row(whole[0])
    return paths, flood


now = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
hour = datetime.timedelta(hours=1)
last_hour, _ = window(now - hour, now)
day, day_flood = window(now - 24 * hour, now)
before, before_flood = window(now - 48 * hour, now - 24 * hour)


def ms(v):
    if v is None:
        return "–"
    return f"{v / 1000:.1f} s" if v >= 1000 else f"{v:.0f} ms"


def size(b):
    return f"{b / 1024:.1f} kB" if b >= 1024 else f"{b:.0f} B"


slow = []
for path, r in day.items():
    p = before.get(path)
    if path in longpoll or not p or r["n"] < MIN_REQUESTS or p["n"] < MIN_REQUESTS:
        continue
    if r["p95"] >= SLOW_FACTOR * p["p95"] and r["p95"] - p["p95"] >= SLOW_BY_MS:
        slow.append(path)

order = sorted(day, key=lambda p: (-day[p]["n"], p))[:top]
served = sum(r["n"] for r in day.values())
head = f"**{zone}: {len(slow)} path{'s' if len(slow) != 1 else ''} slower than the day before.**" if slow else f"**{zone}: answering as fast as the day before.**"
md = [head, ""]
md += [f"⚠ **Slower:** `{p}` p95 {ms(day[p]['p95'])}, was {ms(before[p]['p95'])}, on {day[p]['n']} requests." for p in sorted(slow)]
for name, flood in (("the last 24 hours", day_flood), ("the 24 hours before", before_flood)):
    if flood:
        md.append(f"⚠ **Left out of {name}:** `{flood[0]}`, {flood[1]:.0%} of its requests. Without it, these are what everyone else saw.")
md += ["", f"**By path**, 24 h ({served} requests that reached the origin)", "",
       "| path | requests | p50 | p95 | p99 | p95, last hour | p95, day before | avg size |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
for p in order:
    r, h, b = day[p], last_hour.get(p), before.get(p)
    label = f"`{p}` (long poll)" if p in longpoll else f"`{p}`"
    md.append(f"| {label} | {r['n']} | {ms(r['p50'])} | {ms(r['p95'])} | {ms(r['p99'])} | {ms(h and h['p95'])} | {ms(b and b['p95'])} | {size(r['bytes'] / max(r['n'], 1))} |")
md += ["", f"_{now.strftime('%Y-%m-%d %H:%M')} UTC. Origin response time, from Cloudflare's sampled data: what a cache answers never reaches the origin, and a long poll's time is its wait._"]
report = "\n".join(md) + "\n"

os.makedirs("/output", exist_ok=True)
with open("/output/report.md", "w", encoding="utf-8") as f:
    f.write(report)
print(report, end="")
