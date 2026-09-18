#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Extract compact hierarchical polyglot symbol outlines (classes, interfaces, functions, methods, structs) from source code across 140+ languages using Universal Ctags, omitting implementation bodies for up to 95% token savings.
#: when=Use when the user wants the structure of a source file or codebase (classes, functions, signatures) without reading whole files, or before planning edits across large files.
#: network=none
#: stdin=none
#: param=code_source:required:file:d=Source file mounted at /input/code_source
#: param=file_path:d=Original host path, used only for its extension (e.g. pkg/x.go)
#: param=file_ext:d=Explicit extension override (py, .go, rs)
#: param=language:d=ctags language name for --language-force, or a short extension
import os
import re
import subprocess
import sys
from pathlib import Path

source_path = os.environ.get("CODE_SOURCE", "")
file_path = os.environ.get("FILE_PATH", "").strip()
file_ext = os.environ.get("FILE_EXT", "").strip()
language = os.environ.get("LANGUAGE", "").strip()

if not source_path or not os.path.exists(source_path):
    print(f"Error: code_source file '{source_path}' does not exist", file=sys.stderr)
    sys.exit(1)

with open(source_path, "r", errors="ignore") as f:
    source_content = f.read()

# Resolve file extension or language
# If file_path is supplied, extract its suffix (e.g. "param.go" -> ".go").
# If file_ext is supplied or language looks like an extension (e.g. "py", ".go", "rs"),
# symlink /tmp/input.<ext> so Universal Ctags natively uses its 140+ language extension maps.
target_path = source_path
ext = file_ext

if not ext and file_path:
    ext = Path(file_path).suffix

if not ext and language:
    if language.startswith("."):
        ext = language
    elif len(language) <= 4 and language.isalnum() and language.islower():
        ext = f".{language}"

# If still no extension, check if the first line is a fragletc container shebang
if not ext and not language and source_content.startswith("#!"):
    first_line = source_content.splitlines()[0]
    if "fragletc" in first_line:
        m = re.search(r"--image(?:=|\s+)(?:[^\s/@]+/)?([^\s@:]+)", first_line)
        if m:
            img = m.group(1).lower()
            if any(k in img for k in ("python", "headless-browser")):
                ext = ".py"
            elif any(k in img for k in ("base", "meme", "shell")):
                ext = ".sh"
            elif "node" in img or "javascript" in img:
                ext = ".js"
            elif "ruby" in img:
                ext = ".rb"

if ext:
    if not ext.startswith("."):
        ext = f".{ext}"
    symlink_path = f"/tmp/input{ext}"
    if os.path.lexists(symlink_path):
        os.remove(symlink_path)
    os.symlink(source_path, symlink_path)
    target_path = symlink_path

# Extract fraglet contract directives as first-class symbols
fraglet_tags = []
for idx, line in enumerate(source_content.splitlines(), start=1):
    line_s = line.strip()
    m = re.match(r"^(?:#:|//:|;:)\s*(.*)$", line_s)
    if not m:
        continue
    body = m.group(1).strip()
    if body.startswith("d="):
        fraglet_tags.append({
            "name": body[2:],
            "file": source_path,
            "kind": "directive",
            "line": idx,
            "language": "fraglet",
            "signature": "",
            "scope": ""
        })
        continue
    for tok in body.split():
        if tok.startswith("param="):
            fraglet_tags.append({
                "name": tok[6:],
                "file": source_path,
                "kind": "param",
                "line": idx,
                "language": "fraglet",
                "signature": "",
                "scope": ""
            })
        elif tok.startswith("output="):
            fraglet_tags.append({
                "name": tok[7:],
                "file": source_path,
                "kind": "output",
                "line": idx,
                "language": "fraglet",
                "signature": "",
                "scope": ""
            })

# Run Universal Ctags
cmd = [
    "ctags",
    "-f",
    "-",
    "--fields=+n+K+S+z+l",
    "--sort=no",
]

if language and not ext:
    cmd.append(f"--language-force={language}")

cmd.append(target_path)

cmd.append(source_path)

ctags_tags = []
try:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("!_TAG_"):
            continue

        parts = line.split("\t")
        if len(parts) < 3:
            continue

        name = parts[0]
        file_ref = parts[1]
        field_parts = parts[3:] if len(parts) > 3 else []

        data = {
            "name": name,
            "file": file_ref,
            "kind": "",
            "line": 0,
            "language": "",
            "signature": "",
            "scope": "",
        }

        for fld in field_parts:
            if ":" in fld:
                k, v = fld.split(":", 1)
                if k == "kind":
                    data["kind"] = v
                elif k == "line":
                    try:
                        data["line"] = int(v)
                    except ValueError:
                        pass
                elif k == "language":
                    data["language"] = v
                elif k == "signature":
                    data["signature"] = v
                elif k in ("class", "struct", "interface", "namespace", "module", "union"):
                    data["scope"] = f"{k}:{v}"

        ctags_tags.append(data)
except subprocess.CalledProcessError as e:
    # If ctags fails, fall back to fraglet tags if present
    pass

tags = fraglet_tags + ctags_tags

if not tags:
    print(f"No symbols extracted from {source_path}")
    sys.exit(0)

# Sort by line number
tags.sort(key=lambda t: t.get("line", 0))

display_name = Path(file_path).name if file_path else Path(source_path).name
print(f"# Symbol Outline: {display_name}")
if language:
    print(f"Detected language: {language}")
print(f"Total symbols found: {len(tags)}\n")

for t in tags:
    name = t.get("name", "")
    kind = t.get("kind", "")
    line_num = t.get("line", 0)
    scope = t.get("scope", "")
    signature = t.get("signature", "")

    prefix = "  " if scope else ""
    kind_str = f"[{kind}]" if kind else ""
    line_str = f"L{line_num}:" if line_num else ""

    if scope:
        print(f"{prefix}{line_str:<6} {kind_str:<12} {scope} -> {name}{signature}")
    else:
        print(f"{line_str:<6} {kind_str:<12} {name}{signature}")
