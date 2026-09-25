#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Fetch the catalog tools a project depends on, verify each against its pinned procedure_hash, and pack them into vendor.tar.gz (executable, at their catalog paths, reproducible bytes). The lock file names where the tools are published ("source https://tools.ofthemachine.com") and lists one "<pack>/<stem>.<ext> sha256:<hex>" per line (# comments allowed); the hashes are what manifest.json and every receipt call procedure_hash. A file whose hash does not match is refused and nothing is written, so base_url may fetch from anywhere -- a mirror, or a local `make serve` -- without weakening the pin or changing the recorded source.
#: when=Use when bootstrapping a repository that runs catalog tools from its own Makefile or CI: turn its tools.lock into a verified vendor/ directory before running anything.
#: network=required
#: stdin=none
#: param=lock:required:file:d=tools.lock: a "source <url>" line, then "<pack>/<stem>.<ext> sha256:<hex>" per line
#: param=base_url:d=Fetch from here instead of the lock's source (a mirror, or http://host.docker.internal:8080); integrity comes from the hashes, not the host
#: output=vendor.tar.gz
import gzip
import hashlib
import io
import os
import re
import sys
import tarfile
import urllib.request

LINE = re.compile(r"^([a-z0-9][a-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*)\s+(sha256:[0-9a-f]{64})$")

source, entries = None, []
for n, line in enumerate(open(os.environ["LOCK"], encoding="utf-8"), 1):
    line = line.split("#", 1)[0].strip()
    if not line:
        continue
    if line.startswith("source "):
        source = line.split(None, 1)[1].strip().rstrip("/")
        continue
    m = LINE.match(line)
    if not m:
        print(f"Error: tools.lock line {n}: expected '<pack>/<stem>.<ext> sha256:<hex>', got {line!r}", file=sys.stderr)
        sys.exit(2)
    entries.append(m.groups())
if not entries:
    print("Error: tools.lock lists no tools", file=sys.stderr)
    sys.exit(2)
base = (os.environ.get("BASE_URL", "").strip() or source or "").rstrip("/")
if not base:
    print("Error: tools.lock has no 'source <url>' line and no base_url was given", file=sys.stderr)
    sys.exit(2)
if "://" not in base:
    base = "https://" + base

files, bad = [], []
for path, want in entries:
    try:
        with urllib.request.urlopen(f"{base}/{path}", timeout=60) as resp:
            data = resp.read()
    except OSError as e:
        print(f"Error: cannot fetch {base}/{path}: {e}", file=sys.stderr)
        sys.exit(1)
    got = "sha256:" + hashlib.sha256(data).hexdigest()
    if got != want:
        bad.append(f"{path}: lock says {want[:19]}..., {base} served {got[:19]}...")
    files.append((path, data, got))

if bad:
    print("Error: refusing to vendor; hash mismatch:\n  " + "\n  ".join(bad), file=sys.stderr)
    sys.exit(1)

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w") as tar:
    for path, data, _ in sorted(files):
        info = tarfile.TarInfo(path)
        info.size, info.mode, info.mtime = len(data), 0o755, 0
        tar.addfile(info, io.BytesIO(data))
with gzip.GzipFile("/output/vendor.tar.gz", "wb", mtime=0) as gz:
    gz.write(buf.getvalue())

for path, _, got in files:
    print(f"verified {path} {got[:19]}...")
