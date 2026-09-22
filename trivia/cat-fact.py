#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
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
