#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Type free text into a Roku device's currently focused on-screen keyboard field (e.g. a search box) over its ECP API -- sends one keypress/Lit_<char> per character in a single call, instead of one fraglet run per letter. Pairs with home-automation/roku-keypress.py to navigate to the field first.
#: when=Use when the user asks to type a search query or other text into whatever on-screen text field is currently focused on a Roku.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
#: param=text:required:d=Text to type into the currently focused on-screen field, e.g. "stargate atlantis"
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ip = os.environ["IP"]
text = os.environ["TEXT"]

if not text:
    print("text param is empty", file=sys.stderr)
    sys.exit(1)

for i, ch in enumerate(text):
    key = f"Lit_{ch}"
    url = f"http://{ip}:8060/keypress/{urllib.parse.quote(key)}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except urllib.error.URLError as e:
        print(f"roku type failed at character {i + 1}/{len(text)} ('{ch}'): {e}", file=sys.stderr)
        sys.exit(1)
    if i < len(text) - 1:
        time.sleep(0.15)

print(f"OK: typed {len(text)} characters to {ip}")
