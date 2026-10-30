#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=A Cloudflare zone's traffic over the last 24 minutes, 24 hours and 24 days, drawn and diagnosed: traffic.svg stacks the three as small multiples (requests from clients by status class, the daily Worker quota and today's projection on the days), worker.svg is the Worker's CPU time per hour against the free plan's 10 ms limit, and report.md is a Markdown report (a headline, the golden signals against the 24 hours before, the top talkers by kind of client and path, and diagnostics that name a poller, the side a 5xx came from, CPU headroom and the quota's pace). Clients are counted by kind (a browser by name, else a program), never by address. Read-only; cloudflare/usage is the quota alone, as gauges.
#: when=Use when someone asks what traffic a Cloudflare site or Worker is getting, for a chart of its requests over minutes, hours or days, why it returns errors, who is driving its request count, or how close it is to the daily Workers quota.
#: network=required
#: stdin=none
#: secret=CLOUDFLARE_API_TOKEN:d=A Cloudflare API token with Account Analytics read and Zone read (read-only)
#: param=zone:required:d=The zone (domain) to read, e.g. example.com
#: param=quota:default=100000:d=Worker requests a day the plan allows (the free plan: 100000)
#: param=tz:default=UTC:d=The IANA time zone the charts' times are shown in (the quota's day is always UTC's)
#: param=top:default=5:d=How many top talkers to list
#: output=traffic.svg
#: output=worker.svg
#: output=report.md
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

API = "https://api.cloudflare.com/client/v4"
TEMPFAIL = 75  # a rate limit, a 5xx or a dropped connection may pass: fragletc --retry
CPU_LIMIT_MS = 10  # the free plan's CPU time per invocation

# The diagnostics' thresholds: each flag is one of these rules.
POLLER_SHARE = 0.30  # one kind of client on one path, of the day's requests
ERROR_SHARE = 0.01  # 5xx, of the last two hours' requests (half that over 24 hours)
CPU_WARN = 0.7  # CPU p99, of the limit
QUOTA_WARN, QUOTA_ALARM = 0.8, 1.0
FAST_POLL_S = 5  # long polls whose median wall time is under this are looping

# Colours chosen on the image's own background, so it reads on a light or a
# dark page alike; red only for 5xx.
BG, EDGE, INK, MUTED = "#fbfbfa", "#d8d8d4", "#333333", "#8a8a85"
OK, C4XX, C5XX = "#8196ab", "#e0a030", "#cf4436"


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
try:
    tz = zoneinfo.ZoneInfo(os.environ["TZ"])
except (zoneinfo.ZoneInfoNotFoundError, ValueError):
    fail(f"unknown time zone {os.environ['TZ']!r}", 2)
zones = call("/zones?name=" + urllib.parse.quote(zone))["result"]
if not zones:
    fail(f"no zone {zone} that this token can read")
zone_id, account_id = zones[0]["id"], zones[0]["account"]["id"]

UTC = datetime.timezone.utc
now = datetime.datetime.now(UTC).replace(second=0, microsecond=0)
iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
minute0 = now - datetime.timedelta(minutes=23)
hour_now = now.replace(minute=0)
hour0 = hour_now - datetime.timedelta(hours=23)
prev0 = hour0 - datetime.timedelta(hours=24)
today = now.date()
day0 = today - datetime.timedelta(days=23)
midnight = datetime.datetime.combine(today, datetime.time(), UTC)
hour_ago = now - datetime.timedelta(hours=1)

# Requests from clients only (eyeball): a Worker's own fetch to its origin is
# a second request at the same edge and would count every request twice.
EYE = 'requestSource:"eyeball"'
zv = {"z": zone_id, "m": iso(minute0), "p": iso(prev0), "h": iso(hour0), "e": iso(now + datetime.timedelta(minutes=1)),
      "d": day0.isoformat(), "t": today.isoformat()}
Z = graphql(
    "query($z:String!,$m:Time!,$p:Time!,$h:Time!,$e:Time!,$d:Date!,$t:Date!){viewer{zones(filter:{zoneTag:$z}){"
    f"minutes:httpRequestsAdaptiveGroups(limit:2000,filter:{{datetime_geq:$m,datetime_lt:$e,{EYE}}}){{count dimensions{{datetimeMinute edgeResponseStatus}}}}"
    f"hours:httpRequestsAdaptiveGroups(limit:5000,filter:{{datetime_geq:$p,datetime_lt:$e,{EYE}}}){{count dimensions{{datetimeHour edgeResponseStatus}}}}"
    f"days:httpRequestsAdaptiveGroups(limit:5000,filter:{{date_geq:$d,date_leq:$t,{EYE}}}){{count dimensions{{date edgeResponseStatus}}}}"
    f"talkers:httpRequestsAdaptiveGroups(limit:5000,orderBy:[count_DESC],filter:{{datetime_geq:$h,datetime_lt:$e,{EYE}}}){{count dimensions{{clientRequestPath userAgentBrowser}}}}"
    'origin:httpRequestsAdaptiveGroups(limit:100,filter:{datetime_geq:$h,datetime_lt:$e,requestSource:"edgeWorkerFetch"}){count dimensions{edgeResponseStatus}}'
    "}}}",
    zv,
)["zones"][0]
wv = {"a": account_id, "m": iso(hour_ago), "p": iso(prev0), "h": iso(hour0), "e": iso(now + datetime.timedelta(minutes=1)),
      "d": day0.isoformat(), "t": today.isoformat()}
W = graphql(
    "query($a:String!,$m:Time!,$p:Time!,$h:Time!,$e:Time!,$d:Date!,$t:Date!){viewer{accounts(filter:{accountTag:$a}){"
    "minutes:workersInvocationsAdaptive(limit:2000,filter:{datetime_geq:$m,datetime_lt:$e}){sum{requests} dimensions{datetimeMinute}}"
    "hours:workersInvocationsAdaptive(limit:2000,filter:{datetime_geq:$p,datetime_lt:$e}){sum{requests errors} quantiles{cpuTimeP50 cpuTimeP99} dimensions{datetimeHour}}"
    "days:workersInvocationsAdaptive(limit:2000,filter:{date_geq:$d,date_leq:$t}){sum{requests} dimensions{date}}"
    "day:workersInvocationsAdaptive(limit:100,filter:{datetime_geq:$h,datetime_lt:$e}){sum{requests errors} quantiles{cpuTimeP99 wallTimeP50} dimensions{status}}"
    "prev:workersInvocationsAdaptive(limit:1,filter:{datetime_geq:$p,datetime_lt:$h}){sum{requests errors} quantiles{cpuTimeP99 wallTimeP50}}"
    "}}}",
    wv,
)["accounts"][0]


def at(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def klass(status):
    return "5xx" if status >= 500 else "4xx" if status >= 400 else "ok"


def buckets(rows, key, starts):
    """Requests per bucket by status class, every bucket present."""
    out = {s: {"ok": 0, "4xx": 0, "5xx": 0} for s in starts}
    for r in rows:
        k = key(r["dimensions"])
        if k in out:
            out[k][klass(r["dimensions"]["edgeResponseStatus"])] += r["count"]
    return [out[s] for s in starts]


minutes = [minute0 + datetime.timedelta(minutes=i) for i in range(24)]
hours = [prev0 + datetime.timedelta(hours=i) for i in range(48)]
days = [day0 + datetime.timedelta(days=i) for i in range(24)]
by_minute = buckets(Z["minutes"], lambda d: at(d["datetimeMinute"]), minutes)
by_hour48 = buckets(Z["hours"], lambda d: at(d["datetimeHour"]), hours)
by_day = buckets(Z["days"], lambda d: datetime.date.fromisoformat(d["date"]), days)
prev24, by_hour = by_hour48[:24], by_hour48[24:]
total = lambda b: b["ok"] + b["4xx"] + b["5xx"]
summed = lambda bs, k: sum(b[k] for b in bs)

# The quota: today's Worker requests, and where the day ends if the last
# hour's rate holds (steadier than today's average early in the UTC day).
worker_day = {r["dimensions"]["date"]: r["sum"]["requests"] for r in W["days"]}
used = worker_day.get(today.isoformat(), 0)
rate = sum(r["sum"]["requests"] for r in W["minutes"])
projected = round(used + rate * (midnight + datetime.timedelta(days=1) - now).total_seconds() / 3600)
pace = projected / quota

# The Worker's hours: CPU per hour, and the 24 hours against the 24 before.
w_hour = {at(r["dimensions"]["datetimeHour"]): r for r in W["hours"]}
statuses = {r["dimensions"]["status"]: r for r in W["day"]}
w_req = sum(r["sum"]["requests"] for r in W["day"])
w_err = sum(r["sum"]["errors"] for r in W["day"])
w_cpu99 = max((r["quantiles"]["cpuTimeP99"] for r in W["day"]), default=0) / 1000  # µs → ms
w_wall50 = statuses.get("success", {}).get("quantiles", {}).get("wallTimeP50", 0) / 1e6  # µs → s
prev = W["prev"][0] if W["prev"] else {"sum": {"requests": 0, "errors": 0}, "quantiles": {"cpuTimeP99": 0, "wallTimeP50": 0}}

# Top talkers: a kind of client on a path, a content address being one path.
talk = {}
for g in Z["talkers"]:
    path = re.sub(r"/[0-9a-f]{64}\b", "/<hash>", g["dimensions"]["clientRequestPath"])
    browser = g["dimensions"]["userAgentBrowser"]
    client = "a program" if browser in ("", "Unknown") else browser
    talk[(client, path)] = talk.get((client, path), 0) + g["count"]
talkers = sorted(talk.items(), key=lambda kv: (-kv[1], kv[0]))
day_req = sum(talk.values()) or 1
origin5 = {}
for g in Z["origin"]:
    s = g["dimensions"]["edgeResponseStatus"]
    if s >= 500:
        origin5[s] = origin5.get(s, 0) + g["count"]


def short(n):
    n = round(n)
    for unit, div in (("M", 1e6), ("k", 1e3)):
        if abs(n) >= div:
            v = n / div
            return f"{v:.1f}{unit}".replace(".0" + unit, unit) if v < 100 else f"{v:.0f}{unit}"
    return str(n)


def pct(a, b):
    return f"{a / b:.1%}" if b else "–"


# ---- traffic.svg: three small multiples, each on its own scale ----
# Drawn for a phone: 480 units wide, shown at about 360 px, so text is
# drawn at 13-16 to read at 10-12.
W_PX, PAD_L, PAD_R = 480, 12, 80
PANEL_H, PANEL_GAP, TOP = 120, 56, 44


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>'


def panel(y0, title, unit, data, labels, ghost=None, line=None):
    """Stacked columns (ok, 4xx, 5xx), the last bucket partial (hollow on
    top), the peak marked; ghost extends the last column to a projection,
    line is a dashed level (the quota)."""
    out = [text(PAD_L, y0 - 12, title, 15, INK, weight="bold")]
    plot_w = W_PX - PAD_L - PAD_R
    peak = max(total(b) for b in data)
    top_v = max(peak, ghost or 0, line[0] if line else 0) * 1.08 or 1
    y = lambda v: y0 + PANEL_H - v / top_v * PANEL_H
    bw = plot_w / len(data)
    out.append(f'<line x1="{PAD_L}" y1="{y0 + PANEL_H}" x2="{PAD_L + plot_w}" y2="{y0 + PANEL_H}" stroke="{EDGE}"/>')
    for i, b in enumerate(data):
        x, base = PAD_L + i * bw + 1, 0
        last = i == len(data) - 1
        for k, colour in (("ok", OK), ("4xx", C4XX), ("5xx", C5XX)):
            if b[k]:
                h = b[k] / top_v * PANEL_H
                fill = f'fill="{colour}"' if not last else f'fill="{colour}" fill-opacity="0.45" stroke="{colour}"'
                out.append(f'<rect x="{x:.1f}" y="{y(base + b[k]):.1f}" width="{bw - 2:.1f}" height="{h:.1f}" {fill}/>')
                base += b[k]
        if last and ghost and ghost > base:
            out.append(f'<rect x="{x:.1f}" y="{y(ghost):.1f}" width="{bw - 2:.1f}" height="{(ghost - base) / top_v * PANEL_H:.1f}" fill="none" stroke="{MUTED}" stroke-dasharray="3 2"/>')
            out.append(text(PAD_L + plot_w + 6, y(ghost) + 4, f"pace {short(ghost)}", 13, MUTED))
    if line:
        level, label = line
        out.append(f'<line x1="{PAD_L}" y1="{y(level):.1f}" x2="{PAD_L + plot_w}" y2="{y(level):.1f}" stroke="{C5XX}" stroke-dasharray="6 4"/>')
        out.append(text(PAD_L + plot_w + 6, y(level) + 4, label, 13, C5XX))
    if peak:
        i = max(range(len(data)), key=lambda i: total(data[i]))
        px = PAD_L + i * bw + bw / 2
        out.append(f'<circle cx="{px:.1f}" cy="{y(peak):.1f}" r="3" fill="{INK}"/>')
        # below the dot when a level line runs where the label would be
        ly = y(peak) + 18 if line and abs(y(peak) - y(line[0])) < 18 else y(peak) - 8
        out.append(text(min(max(px, PAD_L + 60), PAD_L + plot_w - 60), ly, f"{short(peak)} at {labels[i]}", 13, INK, "middle"))
    if not line:  # a level line labels the scale itself
        out.append(text(PAD_L + plot_w + 6, y0 + 12, f"{short(top_v / 1.08)}{unit}", 13, MUTED))
    out.append(text(PAD_L + plot_w + 6, y0 + PANEL_H, "0", 13, MUTED))
    for i, x, anchor in ((0, PAD_L, "start"), (len(data) // 2, PAD_L + plot_w / 2, "middle"), (len(data) - 1, PAD_L + plot_w, "end")):
        out.append(text(x, y0 + PANEL_H + 17, labels[i], 13, MUTED, anchor))
    return out


local = lambda t: t.astimezone(tz)
tzname = local(now).strftime("%Z")
H = TOP + 3 * (PANEL_H + PANEL_GAP) + 14
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_PX} {H}" width="{W_PX}" height="{H}" font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
       f'<rect x="0.5" y="0.5" width="{W_PX - 1}" height="{H - 1}" rx="6" fill="{BG}" stroke="{EDGE}"/>',
       text(PAD_L, 26, zone, 16, INK, weight="bold")]
legend_x = W_PX - 12 - 168
for name, colour, width in (("2xx/3xx", OK, 76), ("4xx", C4XX, 46), ("5xx", C5XX, 46)):
    svg.append(f'<rect x="{legend_x}" y="15" width="11" height="11" fill="{colour}"/>')
    svg.append(text(legend_x + 15, 25, name, 13, MUTED))
    legend_x += width
y0 = TOP + 18
svg += panel(y0, "Last 24 minutes", "/min", by_minute, [local(t).strftime("%H:%M") for t in minutes])
y0 += PANEL_H + PANEL_GAP
svg += panel(y0, f"Last 24 hours ({tzname})", "/h", by_hour, [local(t).strftime("%H:00") for t in hours[24:]])
y0 += PANEL_H + PANEL_GAP
svg += panel(y0, "Last 24 days (UTC days)", "/d", by_day, [d.strftime("%b %-d") for d in days],
             ghost=max(projected, total(by_day[-1])), line=(quota, f"quota {short(quota)}"))
svg.append("</svg>")

# ---- worker.svg: CPU per hour against the limit, exceptions beneath ----
WH, PL, PR, PT, PB = 230, 12, 92, 40, 54
plot_w, plot_h = W_PX - PL - PR, WH - PT - PB
cpu50 = [w_hour.get(t, {}).get("quantiles", {}).get("cpuTimeP50", 0) / 1000 for t in hours[24:]]
cpu99 = [w_hour.get(t, {}).get("quantiles", {}).get("cpuTimeP99", 0) / 1000 for t in hours[24:]]
errs = [w_hour.get(t, {}).get("sum", {}).get("errors", 0) for t in hours[24:]]
cmax = max(max(cpu99, default=0), CPU_LIMIT_MS) * 1.1
cx = lambda i: PL + (i + 0.5) * plot_w / 24
cy = lambda v: PT + plot_h - v / cmax * plot_h
wsvg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_PX} {WH}" width="{W_PX}" height="{WH}" font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect x="0.5" y="0.5" width="{W_PX - 1}" height="{WH - 1}" rx="6" fill="{BG}" stroke="{EDGE}"/>',
        text(PL, 26, f"Worker CPU per invocation, 24 h ({tzname})", 16, INK, weight="bold"),
        f'<line x1="{PL}" y1="{cy(CPU_LIMIT_MS):.1f}" x2="{PL + plot_w}" y2="{cy(CPU_LIMIT_MS):.1f}" stroke="{C5XX}" stroke-dasharray="6 4"/>',
        text(PL + plot_w + 6, cy(CPU_LIMIT_MS) + 4, f"limit {CPU_LIMIT_MS} ms", 13, C5XX),
        f'<line x1="{PL}" y1="{PT + plot_h}" x2="{PL + plot_w}" y2="{PT + plot_h}" stroke="{EDGE}"/>']
for series, width, label in ((cpu50, 1.5, "p50"), (cpu99, 2.5, "p99")):
    pts = " ".join(f"{cx(i):.1f},{cy(v):.1f}" for i, v in enumerate(series))
    wsvg.append(f'<polyline points="{pts}" fill="none" stroke="{OK if label == "p50" else INK}" stroke-width="{width}"/>')
    wsvg.append(text(PL + plot_w + 6, cy(series[-1]) + 4, f"{label} {series[-1]:.1f} ms", 13, MUTED))
strip = PT + plot_h + 18
wsvg.append(text(PL, strip + 4, "exceptions", 13, MUTED))
for i, n in enumerate(errs):
    if n:
        wsvg.append(f'<line x1="{cx(i):.1f}" y1="{strip - 6}" x2="{cx(i):.1f}" y2="{strip + 6}" stroke="{C5XX}" stroke-width="3"/>')
for i in (0, 12, 23):
    wsvg.append(text(cx(i), WH - 10, local(hours[24 + i]).strftime("%H:00"), 13, MUTED, "middle"))
wsvg.append("</svg>")

# ---- the diagnostics: each a rule, flagged only when it fires ----
flags, fine = [], []
mark = "🔴" if pace >= QUOTA_ALARM or used >= 0.9 * quota else "⚠" if pace >= QUOTA_WARN else ""
(flags if mark else fine).append(
    f"{mark} **Quota:** {short(used)} Worker requests today (UTC), {short(rate)} in the last hour: on pace for "
    f"**{short(projected)}**, {pace:.0%} of {short(quota)}." if mark else f"quota on pace for {pace:.0%}")
if talkers:
    (client, path), n = talkers[0]
    share = n / day_req
    if share > POLLER_SHARE:
        flags.append(f"⚠ **Poller:** {client} on `{path}` made {short(n)} requests in 24 hours, {share:.0%} of them "
                     f"({n / 1440:.0f}/min).")
    else:
        fine.append("no single client dominates")
since = sum(n for (c, p), n in talk.items() if p.startswith("/v1/since"))
if since / day_req > 0.5 and w_wall50 and w_wall50 < FAST_POLL_S:
    flags.append(f"⚠ **Fast polls:** `/v1/since` is {since / day_req:.0%} of requests and the Worker's median "
                 f"wall time is {w_wall50:.1f} s: long polls are returning early, so a client is looping.")
else:
    fine.append(f"long polls wait ({w_wall50:.0f} s median)")
hour5 = by_hour[-1]["5xx"] + by_hour[-2]["5xx"]
hour_all = total(by_hour[-1]) + total(by_hour[-2])
day5 = summed(by_hour, "5xx")
cur = sum(total(b) for b in by_hour)
errors_flag = bool(hour_all and hour5 / hour_all > ERROR_SHARE or cur and day5 / cur > ERROR_SHARE / 2)
if errors_flag:
    side = []
    if origin5:
        side.append("the origin answered the Worker " + ", ".join(f"{s} ×{short(n)}" for s, n in sorted(origin5.items())))
    if w_err:
        side.append(f"the Worker itself failed {short(w_err)} times")
    flags.append(f"⚠ **5xx:** {short(day5)} in 24 hours, {pct(day5, cur)} of requests ({pct(hour5, hour_all)} in the last two hours); "
                 + ("; ".join(side) or "neither the Worker nor its origin fetches account for them") + "."
                 + (" 530 is the tunnel down, 502 the origin behind it." if {502, 530} & set(origin5) else ""))
else:
    fine.append(f"5xx {pct(day5, cur)}")
exceeded = statuses.get("exceededResources", {}).get("sum", {}).get("requests", 0)
if w_cpu99 > CPU_WARN * CPU_LIMIT_MS or exceeded:
    flags.append(f"⚠ **CPU:** p99 {w_cpu99:.1f} ms of the {CPU_LIMIT_MS} ms limit"
                 + (f"; {exceeded} invocations exceeded their resources" if exceeded else "") + ".")
else:
    fine.append(f"CPU p99 {w_cpu99:.1f} ms of {CPU_LIMIT_MS}")

# ---- report.md ----
if flags:
    worst = flags[0].split("**")[1].rstrip(":")
    head = f"**{zone}: {len(flags)} to look at — {worst.lower()} first. Pace {short(projected)} of {short(quota)} today.**"
else:
    head = f"**{zone}: quiet. {short(used)} Worker requests today, pace {short(projected)} of {short(quota)}, no flags.**"
now_min = (sum(total(b) for b in by_minute[:-1]) / 23) if len(by_minute) > 1 else 0
prv = sum(total(b) for b in prev24)
rows = [
    ("traffic", f"{now_min:.0f}/min", short(cur), short(prv), ""),
    ("5xx", pct(sum(b["5xx"] for b in by_minute), sum(total(b) for b in by_minute)), pct(day5, cur),
     pct(summed(prev24, "5xx"), prv), "⚠" if errors_flag else ""),
    ("4xx", pct(sum(b["4xx"] for b in by_minute), sum(total(b) for b in by_minute)), pct(summed(by_hour, "4xx"), cur),
     pct(summed(prev24, "4xx"), prv), ""),
    ("exceptions", "", short(w_err), short(prev["sum"]["errors"]), "⚠" if w_err else ""),
    ("CPU p99", f"{cpu99[-1]:.1f} ms", f"{w_cpu99:.1f} ms", f"{prev['quantiles']['cpuTimeP99'] / 1000:.1f} ms",
     "⚠" if w_cpu99 > CPU_WARN * CPU_LIMIT_MS else ""),
    ("poll wait p50", "", f"{w_wall50:.0f} s", f"{prev['quantiles']['wallTimeP50'] / 1e6:.0f} s", ""),
]
md = [head, ""]
md += flags + ([""] if flags else [])
md += ["**Golden signals** (requests from clients; the Worker's own below them)", "", "| signal | 24 min | 24 h | 24 h before |", "|---|---:|---:|---:|"]
md += [f"| {name} | {now_v} | {day_v}{' ⚠' if flag else ''} | {prev_v} |" for name, now_v, day_v, prev_v, flag in rows]
md += ["", f"**Top talkers**, 24 h ({short(day_req)} requests)", "", "| client | path | requests | share |", "|---|---|---:|---:|"]
md += [f"| {c} | `{p}` | {short(n)} | {n / day_req:.0%}{' ⚠' if n / day_req > POLLER_SHARE else ''} |" for (c, p), n in talkers[:top]]
md += ["", "_Fine: " + "; ".join(fine) + "._" if fine else "",
       f"_{local(now).strftime('%Y-%m-%d %H:%M %Z')}; the last bucket of each chart is still filling. "
       "Client requests are Cloudflare's sampled estimates; the quota counts the Worker's own invocations._"]
report = "\n".join(line for line in md if line is not None) + "\n"

os.makedirs("/output", exist_ok=True)
for name, body in (("traffic.svg", "\n".join(svg)), ("worker.svg", "\n".join(wsvg)), ("report.md", report)):
    with open(os.path.join("/output", name), "w", encoding="utf-8") as f:
        f.write(body + ("\n" if not body.endswith("\n") else ""))
print(report, end="")
