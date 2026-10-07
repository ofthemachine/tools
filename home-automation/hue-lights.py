#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=List the lights on a Philips Hue bridge via its local v1 API -- one "id\tname\ton\ bri%\treachable" line per light, so a caller can find a light's id (or confirm its name) for home-automation/hue-set.py.
#: when=Use when the user asks what lights exist, their names/ids, or whether a light is on, reachable, and at what brightness.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Hue bridge, e.g. 192.168.0.245
#: secret=HUE_USER:d=Hue API username from link-button pairing (export HUE_USER on the agent host; delivered as a file, never a param, so it stays out of chat and the ledger)
# x-operon: secret=HUE_USER
import json
import os
import sys
import urllib.error
import urllib.request

ip = os.environ["IP"]


def hue_username() -> str:
    # fragletc delivers #: secret= values as a file ($HUE_USER_FILE);
    # the native fallback runner inherits host env directly instead.
    path = os.environ.get("HUE_USER_FILE")
    if path:
        try:
            with open(path) as f:
                if token := f.read().strip():
                    return token
        except OSError as e:
            print(f"hue secret file unreadable: {e}", file=sys.stderr)
            sys.exit(1)
    for var in ("HUE_USER", "USERNAME"):
        if token := os.environ.get(var, "").strip():
            return token
    print("hue username missing: export HUE_USER on the agent host (pair via link button first)", file=sys.stderr)
    sys.exit(1)


username = hue_username()

url = f"http://{ip}/api/{username}/lights"
try:
    with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=10) as resp:
        body = resp.read()
except urllib.error.URLError as e:
    print(f"hue query/lights failed: {e}", file=sys.stderr)
    sys.exit(1)

try:
    lights = json.loads(body)
except json.JSONDecodeError as e:
    print(f"hue query/lights returned non-JSON: {e}", file=sys.stderr)
    sys.exit(1)

if isinstance(lights, list):
    # Bridge answers errors as a list, e.g. [{"error": {"type": 1, ...}}] for bad username
    for item in lights:
        err = item.get("error", {})
        print(f"hue error {err.get('type')}: {err.get('description')}", file=sys.stderr)
    if any("error" in item for item in lights):
        print("hint: username rejected -- re-pair with the link button and export the new HUE_USER", file=sys.stderr)
    sys.exit(1)

for lid in sorted(lights, key=int):
    info = lights[lid]
    st = info.get("state", {})
    on = "on" if st.get("on") else "off"
    bri = st.get("bri")
    bri_pct = f"{round(bri / 254 * 100)}%" if isinstance(bri, int) else "?"
    reachable = "reachable" if st.get("reachable", True) else "UNREACHABLE"
    print(f"{lid}\t{info.get('name', '?')}\t{on}\t{bri_pct}\t{reachable}")
