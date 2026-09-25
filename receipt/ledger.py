#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Typeset an archive of fragletc receipts (fraglet-receipt/2) as a ledger: one row per run with its tool, memo key, params, inputs and outputs by content hash, and exit code, in run order. Where a run's input hash is an earlier run's output hash the row says so, which makes the archive a provenance graph a reader can follow by hand. If the archive also carries blobs/<sha256 hex> files, every hash present in it is marked, so the reader knows which bytes travel with the ledger and which are hash-only. Emits an HTML fragment (default) or Markdown to stdout, for embedding in a page such as a Daily Fraglet edition.
#: when=Use when a bundle of receipts must be presented to a reader as evidence -- an appendix, a ledger page, a provenance table -- rather than handed over as raw JSON.
#: network=none
#: stdin=none
#: param=receipts:required:file:d=tar/tar.gz/zip containing receipts/*.json and optionally blobs/<hex>
#: param=format:default=html:d=html (a fragment with class="ledger") or md
#: param=prefix:default=12:d=How many hex characters of each hash to print
import html
import io
import json
import os
import sys
import tarfile
import zipfile

archive = os.environ["RECEIPTS"]
fmt = os.environ.get("FORMAT", "html").strip().lower()
prefix = int(os.environ.get("PREFIX", "12"))

receipts = []
blobs = set()


def take(name, data):
    base = os.path.basename(name)
    if "/receipts/" in "/" + name and base.endswith(".json"):
        try:
            receipts.append((base, json.loads(data.decode("utf-8"))))
        except (ValueError, UnicodeDecodeError) as e:
            print(f"Error: {name}: {e}", file=sys.stderr)
            sys.exit(2)
    elif "/blobs/" in "/" + name:
        blobs.add(base.replace("sha256_", "sha256:"))


if zipfile.is_zipfile(archive):
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not info.is_dir():
                take(info.filename, z.read(info))
else:
    with tarfile.open(archive) as t:
        for m in t.getmembers():
            if m.isfile():
                take(m.name, t.extractfile(m).read())

if not receipts:
    print("Error: no receipts/*.json in the archive", file=sys.stderr)
    sys.exit(2)

receipts.sort(key=lambda r: r[1].get("started", ""))


def short(h):
    return h.split(":", 1)[-1][:prefix]


def tool_of(r):
    return os.path.basename(r.get("procedure") or "inline")


def unbound(r):
    why = []
    if r.get("argv"):
        why.append("argv")
    if r.get("env"):
        why.append("-e " + ",".join(r["env"]))
    if r.get("stdin_mode") == "stream":
        why.append("stdin streamed")
    return why


def klass(r):
    return "hermetic" if (not unbound(r) and "memo_key" in r and r.get("network") == "none" and "@sha256:" in r.get("image", "")) else "environmental"


# Every output hash, by the run (index) that produced it: the edges of the graph.
produced = {}
for i, (_, r) in enumerate(receipts):
    for name, h in (r.get("outputs") or {}).items():
        produced.setdefault(h, (i, name))

esc = html.escape


def cell_hashes(items, i, stdin_mode=""):
    parts = []
    for name, h in sorted(items.items()):
        if i == "in" and name == "" and stdin_mode == "none":
            continue  # nothing was attached; the empty-input hash is implied by the mode
        label = "stdin" if name == "" and i == "in" else ("stdout" if name == "" else name)
        mark = "&#x2713;" if h in blobs else ""
        src = ""
        if i == "in" and h in produced:
            j, oname = produced[h]
            src = f' <span class="from">&larr; run {j + 1} {esc(tool_of(receipts[j][1]))}</span>'
        parts.append(f"<b>{esc(label)}</b> <code>{short(h)}</code>{mark}{src}")
    return "<br>".join(parts) or "&mdash;"


if fmt == "md":
    print("| # | Tool | Key | Class | Params | Inputs | Outputs | Exit |")
    print("|---|---|---|---|---|---|---|---|")
    for i, (fname, r) in enumerate(receipts):
        key = short(r["memo_key"]) if "memo_key" in r else "unkeyed (" + ", ".join(unbound(r)) + ")"
        # a pipe inside a value (jq filters, meme caption lines) would split the table cell
        params = ", ".join(f"{k}={v.replace('|', chr(92) + '|')}" for k, v in sorted((r.get("params") or {}).items())) or "—"
        ins = ", ".join(f"{k or 'stdin'}={short(h)}" for k, h in sorted((r.get("inputs") or {}).items()))
        outs = ", ".join(f"{k or 'stdout'}={short(h)}" for k, h in sorted((r.get("outputs") or {}).items()))
        print(f"| {i + 1} | {tool_of(r)} | `{key}` | {klass(r)} | {params} | {ins} | {outs} | {r.get('exit_code')} |")
    sys.exit(0)

rows = []
for i, (fname, r) in enumerate(receipts):
    if "memo_key" in r:
        key = f"<code>{short(r['memo_key'])}</code>"
    else:
        key = "<i>unkeyed</i><br><span class=\"from\">" + esc(", ".join(unbound(r))) + "</span>"
    params = "<br>".join(
        f"<b>{esc(k)}</b> {esc(v if len(v) <= 48 else v[:45] + '…')}" for k, v in sorted((r.get("params") or {}).items())
    ) or "&mdash;"
    started = r.get("started", "")[11:19] + "Z"
    rows.append(
        f"<tr><td>{i + 1}</td><td><b>{esc(tool_of(r))}</b><br><span class=\"from\">{started} &middot; {esc(r.get('network') or 'undeclared')}"
        f" &middot; {esc(r.get('stdin_mode', ''))}</span></td><td>{key}<br><span class=\"from\">{klass(r)}</span></td>"
        f"<td>{params}</td><td>{cell_hashes(r.get('inputs') or {}, 'in', r.get('stdin_mode', ''))}</td>"
        f"<td>{cell_hashes(r.get('outputs') or {}, 'out')}</td><td>{r.get('exit_code')}</td></tr>"
    )

hermetic = sum(1 for _, r in receipts if klass(r) == "hermetic")
keyed = sum(1 for _, r in receipts if "memo_key" in r)
edges = sum(1 for _, r in receipts for h in (r.get("inputs") or {}).values() if h in produced)
print(
    f'<div class="ledger-summary">{len(receipts)} runs &middot; {keyed} keyed &middot; {hermetic} hermetic &middot; '
    f"{edges} input{'s' if edges != 1 else ''} traced to an earlier run's output &middot; {len(blobs)} blob{'s' if len(blobs) != 1 else ''} in the bundle "
    f"(&#x2713; marks a hash whose bytes travel with this ledger)</div>"
)
print('<table class="ledger"><thead><tr><th>#</th><th>Run</th><th>Memo key</th><th>Params</th><th>Inputs</th><th>Outputs</th><th>Exit</th></tr></thead><tbody>')
print("\n".join(rows))
print("</tbody></table>")
