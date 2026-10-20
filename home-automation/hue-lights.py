#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=List the lights on a Philips Hue bridge via its local v1 API -- one "id\tname\ton\tbri%\treachable\thex" line per light. hex is the bulb's color as #rrggbb at full brightness (brightness stays in its own column), or "-" when the bulb has no color. hs mode is the inverse of hue-set's hex encoding, so a hex this prints can be sent back.
#: when=Use when the user asks what lights exist, their names/ids, or whether a light is on, reachable, at what brightness, and what color.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Hue bridge, e.g. 192.168.0.245
#: secret=HUE_USER:d=Hue API username from link-button pairing (export HUE_USER on the agent host; delivered as a file, never a param, so it stays out of chat and the ledger)
import colorsys
import json
import math
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


def hue_sat_to_hex(hue: int, sat: int) -> str:
    # Inverse of hue-set's hex → hue/sat, after the same integer quantization.
    # Value is 1: brightness is the bri column, not part of the hex.
    h = max(0, min(65535, hue)) / 65535
    s = max(0, min(254, sat)) / 254
    r, g, b = colorsys.hsv_to_rgb(h, s, 1.0)
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c * 255))) for c in (r, g, b)))


def xy_to_hex(x: float, y: float) -> str:
    # CIE xy at full brightness. Philips sRGB matrix, then gamma.
    if y <= 0:
        return "#000000"
    z = 1.0 - x - y
    big_y = 1.0
    big_x = (big_y / y) * x
    big_z = (big_y / y) * z
    r = big_x * 1.656492 - big_y * 0.354851 - big_z * 0.255038
    g = -big_x * 0.707196 + big_y * 1.655716 + big_z * 0.036152
    b = big_x * 0.051713 - big_y * 0.121364 + big_z * 1.011530
    rgb = [r, g, b]
    peak = max(rgb)
    if peak > 1:
        rgb = [c / peak for c in rgb]

    def correct(c: float) -> int:
        c = max(0.0, c)
        c = 12.92 * c if c <= 0.0031308 else (1.055 * (c ** (1 / 2.4))) - 0.055
        return max(0, min(255, round(c * 255)))

    return "#{:02x}{:02x}{:02x}".format(*(correct(c) for c in rgb))


def ct_to_hex(mired: int) -> str:
    # Mired → kelvin → sRGB (Tanner Helland). Hue's range is 153–500 mired.
    temp = (1_000_000 / mired) / 100 if mired else 0
    if temp <= 0:
        return "#000000"
    if temp <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    if temp >= 66:
        b = 255.0
    elif temp <= 19:
        b = 0.0
    else:
        b = 138.5177312231 * math.log(temp - 10) - 305.0447927307

    def clamp(c: float) -> int:
        return max(0, min(255, round(c)))

    return "#{:02x}{:02x}{:02x}".format(clamp(r), clamp(g), clamp(b))


def state_hex(st: dict) -> str:
    # The bulb's current mode. hue/sat left over from an earlier command are
    # not the color it is showing.
    mode = st.get("colormode")
    if mode == "hs" and isinstance(st.get("hue"), int) and isinstance(st.get("sat"), int):
        return hue_sat_to_hex(st["hue"], st["sat"])
    xy = st.get("xy")
    if mode == "xy" and isinstance(xy, (list, tuple)) and len(xy) == 2:
        return xy_to_hex(float(xy[0]), float(xy[1]))
    if mode == "ct" and isinstance(st.get("ct"), int) and st["ct"] > 0:
        return ct_to_hex(st["ct"])
    return "-"


for lid in sorted(lights, key=int):
    info = lights[lid]
    st = info.get("state", {})
    on = "on" if st.get("on") else "off"
    bri = st.get("bri")
    bri_pct = f"{round(bri / 254 * 100)}%" if isinstance(bri, int) else "?"
    reachable = "reachable" if st.get("reachable", True) else "UNREACHABLE"
    print(f"{lid}\t{info.get('name', '?')}\t{on}\t{bri_pct}\t{reachable}\t{state_hex(st)}")
