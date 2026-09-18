#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=A random piece of advice (Advice Slip API, no API key).
#: when=Use when the user asks for a random piece of advice, or a caption or meme needs one.
#: network=required
#: stdin=none
import sys
import json
import urllib.request

try:
    with urllib.request.urlopen("https://api.adviceslip.com/advice", timeout=15) as resp:
        data = json.load(resp)
except Exception as e:
    print(f"advice request failed: {e}", file=sys.stderr)
    sys.exit(1)

advice = (data.get("slip") or {}).get("advice")
if not advice:
    print("response missing advice", file=sys.stderr)
    sys.exit(1)
print(advice)
