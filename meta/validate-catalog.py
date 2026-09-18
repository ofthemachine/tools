#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Validate a compiled tools catalog (archived): every pack's SKILL.md against the agentskills.io specification using skills-ref, the spec's own reference validator; every tool file present, executable, and hashing to the procedure_hash manifest.json records for it; every llms.txt link resolving; marketplace.json plugins matching the pack directories; and, if an okf/ bundle is present, every concept typed and every relative link resolving. Prints one line per finding and a summary; exit 0 only when clean.
#: when=Use when the user asks whether a compiled catalog of packs is valid, as the catalog build's validation step, or before publishing a catalog.
#: network=none
#: stdin=none
#: param=archive:required:file:d=tar/tar.gz/zip of a compiled catalog: <pack>/SKILL.md and tools, manifest.json, llms.txt, marketplace.json, optional okf/
#: param=strict:default=true:d=Treat warnings (body over 500 lines) as failures when true
import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

import yaml
from skills_ref import validate as skills_ref_validate

MAX_BODY_LINES = 500
LINK_RE = re.compile(r"\]\(([^)#\s]+)\)")
OKF_RESERVED = {"index.md", "log.md"}

archive = os.environ["ARCHIVE"]
strict = os.environ["STRICT"].strip().lower() in ("true", "1", "yes")

root = Path(tempfile.mkdtemp(prefix="catalog_"))
try:
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tar:
            for m in tar.getmembers():
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    print(f"Error: unsafe archive member {m.name!r}", file=sys.stderr)
                    sys.exit(2)
                if not os.path.basename(m.name).startswith("._"):
                    tar.extract(m, root)
    elif zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(root)
    else:
        print("Error: archive is not a tar or zip", file=sys.stderr)
        sys.exit(2)
except Exception as e:
    print(f"Error: cannot unpack archive: {e}", file=sys.stderr)
    sys.exit(2)

# Tolerate one wrapping directory (tar czf catalog.tar.gz catalog).
entries = [p for p in root.iterdir() if not p.name.startswith(".")]
if len(entries) == 1 and entries[0].is_dir() and not (root / "manifest.json").exists():
    root = entries[0]

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def is_executable_file(p: Path) -> bool:
    return p.is_file() and bool(p.stat().st_mode & 0o111)


def frontmatter(text: str):
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        return None, text
    try:
        return (yaml.safe_load(parts[1]) or {}), parts[2]
    except yaml.YAMLError:
        return None, parts[2]


# 1. manifest.json is the structured view every other check is measured against.
manifest_path = root / "manifest.json"
if not manifest_path.exists():
    print("Error: no manifest.json in the archive", file=sys.stderr)
    sys.exit(2)
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
packs = {p["name"]: p for p in manifest.get("packs", [])}
tools = manifest.get("tools", [])
if not packs or not tools:
    print("Error: manifest.json lists no packs or no tools", file=sys.stderr)
    sys.exit(2)

# 2. Every pack: SKILL.md as the spec's own validator sees it, plus the catalog rules.
for name, pack in packs.items():
    pack_dir = root / name
    skill_md = pack_dir / "SKILL.md"
    where = f"{name}/SKILL.md"
    if not skill_md.exists():
        err(f"{where}: missing")
        continue
    errors.extend(f"{where}: {m}" for m in skills_ref_validate(pack_dir))
    fm, body = frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        continue
    if fm.get("name") != name:
        err(f"{where}: name {fm.get('name')!r} must equal the pack directory {name!r}")
    meta = fm.get("metadata") or {}
    if not isinstance(meta, dict):
        err(f"{where}: metadata must be a mapping")
    else:
        for k, v in meta.items():
            if not isinstance(v, str):
                err(f"{where}: metadata.{k} must be a string (spec: string->string map), got {type(v).__name__}")
    n = len(body.splitlines())
    if n > MAX_BODY_LINES:
        warnings.append(f"{where}: body has {n} lines (spec recommends <= {MAX_BODY_LINES}); split the pack by subject")
    for ref in sorted(set(re.findall(r"<skill-dir>/([A-Za-z0-9_.-]+)", body))):
        if ref != "SKILL.md" and not is_executable_file(pack_dir / ref):
            err(f"{where}: body runs <skill-dir>/{ref} but it is missing or not executable beside SKILL.md")
    plugin = pack_dir / ".claude-plugin" / "plugin.json"
    if not plugin.exists():
        err(f"{name}/.claude-plugin/plugin.json: missing")
    else:
        pj = json.loads(plugin.read_text(encoding="utf-8"))
        if pj.get("name") != name:
            err(f"{name}/.claude-plugin/plugin.json: name {pj.get('name')!r} must equal the pack")
    for stem in pack.get("tools", []):
        if not any(t["pack"] == name and t["stem"] == stem for t in tools):
            err(f"manifest.json: pack {name} lists tool {stem!r} that has no tool record")

# 3. Every tool: present, executable, and byte-identical to what was compiled (procedure_hash).
for t in tools:
    p = root / t["path"]
    if t["pack"] not in packs:
        err(f"manifest.json: tool {t['path']} belongs to unknown pack {t['pack']!r}")
    if not is_executable_file(p):
        err(f"{t['path']}: missing or not executable")
        continue
    actual = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != t.get("procedure_hash"):
        err(f"{t['path']}: procedure_hash {actual} differs from manifest.json ({t.get('procedure_hash')}); the copy is not byte-identical")
    if t.get("network") not in ("none", "required"):
        err(f"{t['path']}: network must be 'none' or 'required', got {t.get('network')!r}")

# 4. llms.txt: the H1 and every link resolve.
llms = root / "llms.txt"
if not llms.exists():
    err("llms.txt: missing")
else:
    text = llms.read_text(encoding="utf-8")
    if not text.startswith("# "):
        err("llms.txt: must start with an H1")
    for target in LINK_RE.findall(text):
        if "://" not in target and not (root / target).exists():
            err(f"llms.txt: link {target!r} does not resolve")
    for name in packs:
        if f"[{name}]({name}/SKILL.md)" not in text:
            err(f"llms.txt: pack {name} is not listed")
if not (root / "llms-full.txt").exists():
    err("llms-full.txt: missing")

# 5. marketplace.json: one plugin per pack, sources pointing at the pack directories.
mp = root / ".claude-plugin" / "marketplace.json"
if not mp.exists():
    err(".claude-plugin/marketplace.json: missing")
else:
    m = json.loads(mp.read_text(encoding="utf-8"))
    listed = {pl.get("name"): pl for pl in m.get("plugins", [])}
    for name in packs:
        pl = listed.get(name)
        if pl is None:
            err(f"marketplace.json: no plugin for pack {name}")
        elif pl.get("source") != f"./{name}":
            err(f"marketplace.json: plugin {name} source {pl.get('source')!r} must be './{name}'")
    for name in listed:
        if name not in packs:
            err(f"marketplace.json: plugin {name!r} has no pack directory")

# 6. OKF bundle, if present.
okf = root / "okf"
okf_count = 0
if okf.is_dir():
    for md in sorted(okf.rglob("*.md")):
        okf_count += 1
        where = str(md.relative_to(root))
        fm, body = frontmatter(md.read_text(encoding="utf-8"))
        if fm is None:
            err(f"{where}: OKF concept without YAML frontmatter")
            continue
        if md.name not in OKF_RESERVED and not (isinstance(fm.get("type"), str) and fm["type"].strip()):
            err(f"{where}: OKF concept needs a non-empty 'type'")
        for target in LINK_RE.findall(body):
            if "://" in target:
                continue
            resolved = (okf / target.lstrip("/")) if target.startswith("/") else (md.parent / target)
            if not resolved.resolve().exists():
                err(f"{where}: link {target!r} does not resolve")

for w in warnings:
    print(f"[WARN] {w}")
for e in errors:
    print(f"[ERROR] {e}")
print(f"packs: {len(packs)}  tools: {len(tools)}  okf concepts: {okf_count}  errors: {len(errors)}  warnings: {len(warnings)}")
if errors or (strict and warnings):
    sys.exit(1)
print("VERDICT: VALID -- skills-ref, catalog rules, llms.txt, marketplace" + (", OKF bundle" if okf_count else ""))
