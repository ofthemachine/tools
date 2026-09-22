#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=List the apps installed on a Roku device via its ECP API -- one "id\tname\tversion" line per app, so a caller can find an app's numeric id for home-automation/roku-launch.py.
#: when=Use when the user asks what apps or channels are installed on a Roku, or needs an app's numeric id before launching it.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ip = os.environ["IP"]
url = f"http://{ip}:8060/query/apps"

req = urllib.request.Request(url, method="GET")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
except urllib.error.URLError as e:
    print(f"roku query/apps failed: {e}", file=sys.stderr)
    sys.exit(1)

root = ET.fromstring(body)
for app in root.findall("app"):
    print(f"{app.get('id')}\t{app.text}\t{app.get('version')}")
