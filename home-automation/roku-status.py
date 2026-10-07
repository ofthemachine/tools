#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Ask a Roku what it is doing right now via ECP queries -- the foreground app (query/active-app) plus player state/position/duration when the app reports them (query/media-player). Read-only: touches nothing on screen, safe to run mid-playback.
#: when=Use when the user asks what is playing, which app is open, or how far into something the Roku is -- or before a relaunch/resume, to record the app (and position, when available) to go back to.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ip = os.environ["IP"]


def ecp_get(path: str) -> bytes:
    url = f"http://{ip}:8060/{path}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=10) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"roku query failed on {path}: {e}", file=sys.stderr)
        sys.exit(1)


def fmt_ms(raw: str) -> str:
    try:
        total_s = int(raw.strip().split()[0]) // 1000
    except (ValueError, IndexError):
        return raw
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# Device capabilities (OS 15+): whether Roku can actually drive TV power
# and audio volume on this rig (HDMI-CEC). If audio-volume is false here,
# VolumeUp/Down/Mute are no-ops -- volume lives on the TV/soundbar, not
# the Roku, and no ECP key will ever move it.
try:
    info = ET.fromstring(ecp_get("query/device-info"))
    tv_power = info.findtext("supports-tv-power-control", default="?").strip()
    audio_vol = info.findtext("supports-audio-volume-control", default="?").strip()
    print(f"device: tv-power-control={tv_power} audio-volume-control={audio_vol}")
except ET.ParseError:
    pass

# Foreground app -- always reported.
root = ET.fromstring(ecp_get("query/active-app"))
app = root.find("app")
app_id = app.get("id") if app is not None else "?"
app_name = (app.text or "?").strip() if app is not None else "?"
app_ver = app.get("version", "?") if app is not None else "?"
print(f"app: {app_name} (id {app_id}, v{app_ver})")

# Player state -- only apps built on Roku's stock video player report this.
# Custom-player apps (Netflix, YouTube, Prime, Disney+, HBO) answer with
# error=true or nothing usable; that is a Roku platform limit, not a bug.
try:
    player = ET.fromstring(ecp_get("query/media-player"))
except ET.ParseError:
    player = None

if player is None or player.get("error", "false") == "true":
    print("player: no position info (app uses a custom player -- see NOTES)")
    print("NOTES: relaunch the same title to resume; the app's own continue-watching picks up where it left off. No universal seek-to-offset exists in ECP.")
    sys.exit(0)

state = player.get("state", "?")
pos = player.findtext("position", default="?").strip()
dur = player.findtext("duration", default="?").strip()
live = player.findtext("is_live", default="false").strip()
line = f"player: state={state} position={fmt_ms(pos)}"
if dur != "?":
    line += f" / duration={fmt_ms(dur)}"
if live == "true":
    line += " (live)"
print(line)
