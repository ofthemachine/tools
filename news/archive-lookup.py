#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=Look up whether archive.ph already has a snapshot of a URL -- GET /newest/<url> and report its Location header on a redirect. Lookup only: never submits a new snapshot, so it can't be used to force-archive something that isn't already there. Prints nothing (not an error) when no snapshot exists -- the caller falls back to the original link.
#: when=Use when a link may be paywalled or gone and the user wants an existing archive.ph snapshot of it, without creating one.
#: network=required
#: stdin=none
#: param=url:required:d=URL to look up on archive.ph
import http.client
import os
import sys

target = os.environ.get("URL", "").strip()
if not target:
    print("archive-lookup: missing url", file=sys.stderr)
    sys.exit(1)

conn = http.client.HTTPSConnection("archive.ph", timeout=20)
try:
    conn.request("GET", "/newest/" + target, headers={"User-Agent": "Mozilla/5.0"})
    resp = conn.getresponse()
    resp.read()
    if resp.status in (301, 302, 303, 307, 308):
        loc = resp.getheader("Location")
        if loc:
            print(loc)
except OSError as e:
    print(f"archive-lookup: request failed: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    conn.close()
