#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=A random cat fact (catfact.ninja, no API key).
#: when=Use when the user asks for a cat fact, or a caption or meme needs one.
#: network=required
#: stdin=none
import sys
import json
import urllib.request

req = urllib.request.Request("https://catfact.ninja/fact", headers={"User-Agent": "ofthemachine-tools (https://github.com/ofthemachine/tools)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
except Exception as e:
    print(f"cat fact request failed: {e}", file=sys.stderr)
    sys.exit(1)

fact = data.get("fact")
if not fact:
    print("response missing fact", file=sys.stderr)
    sys.exit(1)
print(fact)
