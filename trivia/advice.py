#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
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
