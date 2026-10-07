#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Set a Philips Hue light (or all lights) via the bridge's local v1 API -- on/off/toggle, brightness percent, white temperature (kelvin or mired), color by hue degrees + saturation percent or by hex (e.g. hex=#ff8000). Light by numeric id or by name (exact then substring match, like home-automation/roku-launch.py); id=all drives group 0. Pairs with home-automation/hue-lights.py for discovery.
#: when=Use when the user asks to turn a light on or off, dim/brighten, or change its color or warmth -- e.g. "turn off the kitchen", "dim living room to 30", "warm the bedroom".
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Hue bridge, e.g. 192.168.0.245
#: secret=HUE_USER:d=Hue API username from link-button pairing (export HUE_USER on the agent host; delivered as a file, never a param, so it stays out of chat and the ledger)
#: param=id:required:d=Numeric light id, light name (e.g. "kitchen"), or "all" for every light
#: param=on:kind=enum(on|off|toggle):d=on, off, or toggle (toggle reads current state first; for "all", any-on means all-off)
#: param=bri:kind=range(0..100):d=Brightness 0-100 percent (0 turns the light off)
#: param=temp:kind=range(2000..6500,100):d=White point in kelvin, e.g. 2700 warm / 4000 neutral / 6500 daylight (mutually exclusive with ct)
#: param=ct:kind=range(153..500):d=White point in mired, 153-500 (Hue-native; mutually exclusive with temp)
#: param=hue:kind=range(0..360):d=Color hue in degrees 0-360 (needs a color-capable bulb)
#: param=sat:kind=range(0..100):d=Color saturation 0-100 percent (pairs with hue)
#: param=hex:kind=color:d=Hex color like #ff8000 or ff8000 (3 or 6 digits, # optional); shorthand for hue+sat, mutually exclusive with them
#: param=transition:kind=number:d=Fade time in seconds (Hue transitiontime is deciseconds; default bridge 0.4s)
#: param=name:d=New name for the light on the bridge (e.g. name="Living room"; id=all refused)
#: param=delete:kind=bool:d=Set true to DELETE this light from the bridge (numeric id only -- names and all refused; irreversible)
# x-operon: secret=HUE_USER
import colorsys
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
light_id = os.environ["ID"]
on_raw = os.environ.get("ON", "").strip().lower()
bri_raw = os.environ.get("BRI", "").strip()
temp_raw = os.environ.get("TEMP", "").strip()
ct_raw = os.environ.get("CT", "").strip()
hue_raw = os.environ.get("HUE", "").strip()
sat_raw = os.environ.get("SAT", "").strip()
hex_raw = os.environ.get("HEX", "").strip()
trans_raw = os.environ.get("TRANSITION", "").strip()
name_raw = os.environ.get("NAME", "").strip()
delete_raw = os.environ.get("DELETE", "").strip().lower()


def hue_api(path: str, method: str = "GET", payload=None):
    url = f"http://{ip}/api/{username}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"hue {method} {path} failed: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"hue {method} {path} returned non-JSON: {e}", file=sys.stderr)
        sys.exit(1)


def check_errors(resp, what: str) -> None:
    if isinstance(resp, list):
        errs = [i["error"] for i in resp if "error" in i]
        for e in errs:
            print(f"hue error {e.get('type')}: {e.get('description')}", file=sys.stderr)
        if errs:
            if any(e.get("type") == 1 for e in errs):
                print("hint: username rejected -- re-pair with the link button and export the new HUE_USER", file=sys.stderr)
            sys.exit(1)


def hex_to_hue_sat(spec: str) -> tuple:
    """#ff8000 (or ff8000, or #f80) to (degrees 0-360, percent 0-100)."""
    h = spec.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        print(f"hex must be 3 or 6 hex digits (e.g. #ff8000), got {spec!r}", file=sys.stderr)
        sys.exit(1)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ss, _ = colorsys.rgb_to_hsv(r, g, b)
    return hh * 360, ss * 100


def resolve_id(name: str) -> str:
    if name.lower() == "all":
        return "all"
    if name.isdigit():
        return name
    lights = hue_api("/lights")
    check_errors(lights, "lights")
    target = name.strip().lower()
    names = {lid: (info.get("name") or "") for lid, info in lights.items()}
    exact = [lid for lid, n in names.items() if n.lower() == target]
    if exact:
        print(f"Resolved light '{name}' to {names[exact[0]]} (id {exact[0]})")
        return exact[0]
    sub = [lid for lid, n in names.items() if target in n.lower()]
    if sub:
        print(f"Resolved light '{name}' to {names[sub[0]]} (id {sub[0]})")
        return sub[0]
    avail = ", ".join(f"{n} ({lid})" for lid, n in sorted(names.items(), key=lambda kv: int(kv[0])))
    print(f"Light '{name}' not found. Available lights: {avail}", file=sys.stderr)
    sys.exit(1)


def want_toggle() -> bool:
    return on_raw == "toggle"


target = resolve_id(light_id)

if delete_raw in ("true", "1", "yes", "on"):
    if not light_id.isdigit():
        print(f"delete needs a numeric id (got {light_id!r}): run hue-lights to confirm it", file=sys.stderr)
        sys.exit(1)
    if on_raw or bri_raw or temp_raw or ct_raw or hue_raw or sat_raw or hex_raw or trans_raw or name_raw:
        print("delete does not combine with on/bri/temp/ct/hue/sat/hex/transition/name -- pass delete=true alone", file=sys.stderr)
        sys.exit(1)
    resp = hue_api(f"/lights/{light_id}", "DELETE")
    check_errors(resp, "delete")
    print(f"OK: deleted light {light_id} from bridge {ip}")
    sys.exit(0)
elif delete_raw != "":
    print(f"delete must be true, got {delete_raw!r}", file=sys.stderr)
    sys.exit(1)

# Toggle needs the current on/off first (for "all": any light on means turn all off).
if want_toggle():
    if target == "all":
        lights = hue_api("/lights")
        check_errors(lights, "lights")
        turn_on = not any(info.get("state", {}).get("on") for info in lights.values())
    else:
        st = hue_api(f"/lights/{target}")
        check_errors(st, f"lights/{target}")
        turn_on = not st.get("state", {}).get("on")
    on_val = turn_on
elif on_raw in ("on", "true", "1", "yes"):
    on_val = True
elif on_raw in ("off", "false", "0", "no"):
    on_val = False
elif on_raw == "":
    on_val = None
else:
    print(f"on must be on/off/toggle, got {on_raw!r}", file=sys.stderr)
    sys.exit(1)

state = {}
if on_val is not None:
    state["on"] = on_val
if bri_raw != "":
    try:
        pct = float(bri_raw)
    except ValueError:
        print(f"bri must be 0-100, got {bri_raw!r}", file=sys.stderr)
        sys.exit(1)
    if not 0 <= pct <= 100:
        print(f"bri must be 0-100, got {bri_raw!r}", file=sys.stderr)
        sys.exit(1)
    if pct == 0:
        state["on"] = False
    else:
        state["bri"] = max(1, round(pct / 100 * 254))
        if on_val is None:
            state["on"] = True
if temp_raw != "" and ct_raw != "":
    print("temp and ct are mutually exclusive -- pass one", file=sys.stderr)
    sys.exit(1)
if temp_raw != "":
    try:
        kelvin = float(temp_raw)
        mired = round(1_000_000 / kelvin)
    except (ValueError, ZeroDivisionError):
        print(f"temp must be kelvin, got {temp_raw!r}", file=sys.stderr)
        sys.exit(1)
    if not 153 <= mired <= 500:
        print(f"temp {temp_raw}K = {mired} mired, outside Hue range 153-500 (try 2000-6500K)", file=sys.stderr)
        sys.exit(1)
    state["ct"] = mired
if ct_raw != "":
    try:
        mired = int(ct_raw)
    except ValueError:
        print(f"ct must be 153-500 mired, got {ct_raw!r}", file=sys.stderr)
        sys.exit(1)
    if not 153 <= mired <= 500:
        print(f"ct must be 153-500 mired, got {ct_raw!r}", file=sys.stderr)
        sys.exit(1)
    state["ct"] = mired
if hex_raw != "":
    if hue_raw != "" or sat_raw != "":
        print("hex replaces hue+sat -- pass one form, not both", file=sys.stderr)
        sys.exit(1)
    deg, spct = hex_to_hue_sat(hex_raw)
    state["hue"] = min(65535, round(deg / 360 * 65535))
    state["sat"] = min(254, round(spct / 100 * 254))
    if on_val is None and "on" not in state:
        state["on"] = True
elif hue_raw != "" or sat_raw != "":
    if hue_raw == "" or sat_raw == "":
        print("hue and sat go together -- pass both", file=sys.stderr)
        sys.exit(1)
    try:
        deg, spct = float(hue_raw), float(sat_raw)
    except ValueError:
        print(f"hue must be 0-360 and sat 0-100, got {hue_raw!r}/{sat_raw!r}", file=sys.stderr)
        sys.exit(1)
    if not 0 <= deg <= 360 or not 0 <= spct <= 100:
        print(f"hue must be 0-360 and sat 0-100, got {hue_raw!r}/{sat_raw!r}", file=sys.stderr)
        sys.exit(1)
    state["hue"] = min(65535, round(deg / 360 * 65535))
    state["sat"] = min(254, round(spct / 100 * 254))
    if on_val is None and "on" not in state:
        state["on"] = True
if trans_raw != "":
    try:
        state["transitiontime"] = max(0, round(float(trans_raw) * 10))
    except ValueError:
        print(f"transition must be seconds, got {trans_raw!r}", file=sys.stderr)
        sys.exit(1)

if not state and not name_raw:
    print("nothing to do: pass on, bri, temp/ct, hue+sat/hex, and/or name", file=sys.stderr)
    sys.exit(1)

if name_raw:
    if target == "all":
        print("name refuses id=all: rename one light at a time", file=sys.stderr)
        sys.exit(1)
    check_errors(hue_api(f"/lights/{target}", "PUT", {"name": name_raw}), "rename")
    print(f"OK: renamed light {target} to {name_raw!r} on {ip}")

if not state:
    sys.exit(0)

if target == "all":
    resp = hue_api("/groups/0/action", "PUT", state)
else:
    resp = hue_api(f"/lights/{target}/state", "PUT", state)
check_errors(resp, "state")

applied = ", ".join(f"{k}={v}" for k, v in state.items())
who = "all lights" if target == "all" else f"light {target}"
print(f"OK: set {who} on {ip}: {applied}")
