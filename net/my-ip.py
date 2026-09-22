#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=The host's public IPv4/IPv6 address as the internet sees it, from ifconfig.me (no API key) -- what `curl ifconfig.me` prints, as a fraglet so a workflow can record where it ran. Prints the bare address and nothing else.
#: when=Use when the user asks what their public IP is, or a workflow needs the address it is running from -- for example to locate itself with net/geo-ip.py.
#: network=required
#: stdin=none
import sys
import urllib.request

req = urllib.request.Request("https://ifconfig.me/ip", headers={"User-Agent": "curl"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        ip = resp.read().decode("ascii", "replace").strip()
except Exception as e:
    print(f"ip lookup failed: {e}", file=sys.stderr)
    sys.exit(1)

if not ip or " " in ip:
    print(f"unexpected response: {ip!r}", file=sys.stderr)
    sys.exit(1)
print(ip)
