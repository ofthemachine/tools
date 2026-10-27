#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=A zone's Worker requests today (the UTC day Cloudflare's daily quota counts) against that quota: how many so far, where the day ends if the last hour's rate holds, and the share of the quota that is, by Worker script; then the last hour's requests to the zone by path and by kind of client (a browser by name, else a program), never by address. The gauges are files (used.txt, projected.txt, share.txt, the projected share as a fraction) and stdout is a short report. Read-only: the token needs only Analytics read and Zone read.
#: when=Use when someone asks how close a Cloudflare Workers site is to its daily request limit, what is driving its request count, or whether a client is polling too hard.
#: network=required
#: stdin=none
#: secret=CLOUDFLARE_API_TOKEN:d=A Cloudflare API token with Account Analytics read and Zone read (read-only)
#: param=zone:required:d=The zone (domain) whose Workers to read, e.g. example.com
#: param=quota:default=100000:d=Worker requests a day the plan allows (the free plan: 100000)
#: param=top:default=8:d=How many paths and clients to list
#: output=used.txt
#: output=projected.txt
#: output=share.txt
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


def fail(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


token = open(os.environ["CLOUDFLARE_API_TOKEN_FILE"], encoding="utf-8").read().strip()


def call(path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
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


def graphql(query, variables):
    return call("/graphql", {"query": query, "variables": variables})["data"]["viewer"]


zone = os.environ["ZONE"].strip().lower()
quota = int(os.environ["QUOTA"])
top = int(os.environ["TOP"])
zones = call("/zones?name=" + urllib.parse.quote(zone))["result"]
if not zones:
    fail(f"no zone {zone} that this token can read")
zone_id, account_id = zones[0]["id"], zones[0]["account"]["id"]

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
day = now.replace(hour=0, minute=0, second=0)
hour = now - datetime.timedelta(hours=1)
iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")

def workers(since):
    return graphql(
        "query($a:String!,$s:Time!,$e:Time!){viewer{accounts(filter:{accountTag:$a}){"
        "workersInvocationsAdaptive(limit:50,filter:{datetime_geq:$s,datetime_leq:$e}){sum{requests errors} dimensions{scriptName}}}}}",
        {"a": account_id, "s": iso(since), "e": iso(now)},
    )["accounts"][0]["workersInvocationsAdaptive"]


scripts = workers(day)
used = sum(s["sum"]["requests"] for s in scripts)
errors = sum(s["sum"]["errors"] for s in scripts)
# Where the day ends if the last hour's rate holds: steadier than today's
# average, which early in the UTC day is a few minutes stretched to 24 hours.
rate = sum(s["sum"]["requests"] for s in workers(hour))
left = (day + datetime.timedelta(days=1) - now).total_seconds() / 3600
projected = round(used + rate * left)
share = projected / quota

# The last hour, by path and by kind of client: what drives the count.
# Never by address: this report is posted where others read it.
groups = graphql(
    "query($z:String!,$s:Time!,$e:Time!){viewer{zones(filter:{zoneTag:$z}){"
    "httpRequestsAdaptiveGroups(limit:200,orderBy:[count_DESC],filter:{datetime_geq:$s,datetime_leq:$e,requestSource:\"eyeball\"})"
    "{count dimensions{clientRequestPath userAgentBrowser}}}}}",
    {"z": zone_id, "s": iso(hour), "e": iso(now)},
)["zones"][0]["httpRequestsAdaptiveGroups"]
paths, clients = {}, {}
for g in groups:
    # a content address is one path, whatever it names
    path = re.sub(r"/[0-9a-f]{64}\b", "/<hash>", g["dimensions"]["clientRequestPath"])
    browser = g["dimensions"]["userAgentBrowser"]
    client = "a program (no browser)" if browser in ("", "Unknown") else browser
    paths[path] = paths.get(path, 0) + g["count"]
    clients[client] = clients.get(client, 0) + g["count"]

os.makedirs("/output", exist_ok=True)
for name, value in (("used.txt", used), ("projected.txt", projected), ("share.txt", round(share, 3))):
    with open(os.path.join("/output", name), "w", encoding="utf-8") as f:
        f.write(f"{value}\n")

ranked = lambda d: sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
print(f"{zone}: {used} Worker requests since {iso(day)} ({errors} errors); {rate} in the last hour, so {projected} "
      f"by the day's end if that holds: {share:.0%} of {quota}.")
for s in sorted(scripts, key=lambda s: -s["sum"]["requests"]):
    print(f"  script {s['dimensions']['scriptName']}: {s['sum']['requests']}")
print(f"The last hour, {sum(paths.values())} requests:")
for path, n in ranked(paths):
    print(f"  {n:6d}  {path}")
for client, n in ranked(clients):
    print(f"  {n:6d}  {client}")
