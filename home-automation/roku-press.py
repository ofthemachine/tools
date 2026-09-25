#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Send one or more remote-control key presses to a Roku device over its ECP API (no auth, LAN only) -- the same buttons as the physical remote: navigation, Select, Home, Back, playback, volume, channel. Pass a comma-separated list (e.g. "Down,Down,Down,Select") to send a whole sequence in one call instead of one fraglet run per key.
#: when=Use when the user asks to control a Roku -- press a remote button or a sequence of buttons, navigate menus, play/pause, change volume or channel, or go Home -- by its LAN IP address.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
#: param=key:required:d=One ECP key name, or a comma-separated sequence, e.g. "Down,Down,Down,Select". Keys: Home, Back, Select, Up, Down, Left, Right, Play, Rev, Fwd, InstantReplay, Info, Search, Enter, Backspace, VolumeUp, VolumeDown, VolumeMute, PowerOff, ChannelUp, ChannelDown
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ip = os.environ["IP"]
keys = [k.strip() for k in os.environ["KEY"].split(",") if k.strip()]

if not keys:
    print("key param yielded no keys after splitting on ','", file=sys.stderr)
    sys.exit(1)

for i, key in enumerate(keys):
    url = f"http://{ip}:8060/keypress/{urllib.parse.quote(key)}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"OK: sent {key} to {ip} (status {resp.status})")
    except urllib.error.URLError as e:
        print(f"roku keypress failed on '{key}' (key {i + 1}/{len(keys)}): {e}", file=sys.stderr)
        sys.exit(1)
    if i < len(keys) - 1:
        time.sleep(0.25)
