#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Fetch a random humorous joke or one-liner (icanhazdadjoke.com, no API key).
#: when=Use when the user asks for a joke or one-liner, or a caption or meme needs one.
#: network=required
#: stdin=none
import sys
import urllib.request

req = urllib.request.Request(
    "https://icanhazdadjoke.com/",
    headers={
        "Accept": "text/plain",
        "User-Agent": "ofthemachine-tools (https://github.com/ofthemachine/tools)",
    },
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        joke = resp.read().decode("utf-8").strip()
except Exception as e:
    print(f"joke request failed: {e}", file=sys.stderr)
    sys.exit(1)

if not joke:
    print("response missing joke text", file=sys.stderr)
    sys.exit(1)

print(joke)
