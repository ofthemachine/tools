#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Launch an app on a Roku device via its ECP API, optionally deep-linking straight into a piece of content when the app supports it (e.g. a Netflix title id) -- pairs with home-automation/roku-apps.py for the app_id.
#: when=Use when the user asks to open an app or channel on a Roku, or to jump straight to a specific show or movie inside one via a deep link.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
#: param=app_id:required:d=App name (e.g. Netflix, YouTube) or numeric app id from home-automation/roku-apps.py
#: param=content_id:d=App-specific content id to deep-link to (e.g. a Netflix title id from its netflix.com/title/<id> URL)
#: param=media_type:d=Content type for the deep link, e.g. movie, series, episode
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ip = os.environ["IP"]
app_id = os.environ["APP_ID"]
content_id = os.environ.get("CONTENT_ID", "")
media_type = os.environ.get("MEDIA_TYPE", "")

# If app_id is not all digits, resolve it against installed apps on the device
if not app_id.isdigit():
    apps_url = f"http://{ip}:8060/query/apps"
    try:
        with urllib.request.urlopen(urllib.request.Request(apps_url, method="GET"), timeout=10) as resp:
            apps_xml = resp.read()
        root = ET.fromstring(apps_xml)
        apps = [(a.get("id"), a.text or "") for a in root.findall("app")]
        target = app_id.strip().lower()
        matched = [a for a in apps if a[1].lower() == target]
        if not matched:
            matched = [a for a in apps if target in a[1].lower()]
        if matched:
            matched_id, matched_name = matched[0]
            print(f"Resolved app '{app_id}' to {matched_name} (id {matched_id})")
            app_id = matched_id
        else:
            avail = ", ".join(f"{name} ({aid})" for aid, name in apps)
            print(f"App '{app_id}' not found on {ip}. Available apps: {avail}", file=sys.stderr)
            sys.exit(1)
    except urllib.error.URLError as e:
        print(f"roku query/apps failed while resolving '{app_id}': {e}", file=sys.stderr)
        sys.exit(1)

query = {}
if content_id:
    query["contentId"] = content_id
if media_type:
    query["mediaType"] = media_type

url = f"http://{ip}:8060/launch/{urllib.parse.quote(app_id)}"
if query:
    url += "?" + urllib.parse.urlencode(query)

req = urllib.request.Request(url, method="POST")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"OK: launched app {app_id} on {ip} (status {resp.status})")
except urllib.error.URLError as e:
    print(f"roku launch failed: {e}", file=sys.stderr)
    sys.exit(1)
