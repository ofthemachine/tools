#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Real current conditions for any city, via wttr.in's compact one-line format (%l: +%t %C) -- genuinely current, not a canned response. Outputs a single short phrase ready for captions or notifications, avoiding unrenderable emoji glyphs.
#: when=Use when the user asks what the weather is like right now somewhere, or a caption or notification needs a live conditions phrase.
#: network=required
#: stdin=none
#: param=location:required:d=City, region, or landmark, e.g. Vancouver or Mount Fuji
import os
import sys
import urllib.parse
import urllib.request

location = os.environ["LOCATION"]
url = "https://wttr.in/" + urllib.parse.quote(location) + "?format=%l:+%t+%C"

req = urllib.request.Request(url, headers={"User-Agent": "curl"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(resp.read().decode("utf-8", "replace").strip())
except urllib.error.URLError as e:
    print(f"weather lookup failed: {e}", file=sys.stderr)
    sys.exit(1)
