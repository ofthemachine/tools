#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Compile a catalog of level-0 tools -- a tarball of pack directories, each an index.md plus fraglet files -- into its projections: one Agent Skill per pack (SKILL.md beside byte-identical copies of the tools), a Claude Code plugin per pack with a marketplace.json, llms.txt and llms-full.txt for agents arriving over HTTP, manifest.json with every tool's contract and procedure_hash, and an Open Knowledge Format bundle. Everything is derived from the tools' own headers and the pack index files; nothing is authored twice.
#: when=Use when the user asks to build, rebuild, or regenerate the tools catalog, or wants the skills, llms.txt, marketplace, or OKF views of a set of fraglet tools.
#: network=none
#: stdin=none
#: param=archive:required:file:d=tar/tar.gz of the catalog source: index.md at the top level (optionally CONTRIBUTING.md beside it, copied through verbatim) plus one directory per pack (<pack>/index.md and the pack's tool files)
#: param=host:default=tools.ofthemachine.com:d=Canonical host (served over https) where the catalog is published; OKF concepts locate computations by URL there, paired with procedure_hash
#: output=catalog.tar.gz
"""
One parse, N renders.

A pack is a directory with an index.md and at least one shebang file. A tool is a shebang file.
Every projection below is a function of (tool headers, pack index.md, root index.md) and nothing
else, so the whole catalog is reproducible from the tarball alone.

  <pack>/SKILL.md              one Agent Skill per pack: frontmatter is exactly what agentskills.io
                               allows (name, description, compatibility, string->string metadata);
                               the body is the pack's tool table
  <pack>/<tool>                byte-identical copies, mode preserved: the path a tool has in the
                               repo is the path it has here and on the web
  <pack>/.claude-plugin/plugin.json, .claude-plugin/marketplace.json
                               a Claude Code plugin per pack
  llms.txt, llms-full.txt      llmstxt.org: packs -> SKILL.md -> tool, two fetches
  CONTRIBUTING.md              the source's, verbatim, when present: how to author a tool
  manifest.json                the structured view (typed params, procedure_hash) for tooling
  okf/                         Open Knowledge Format v0.2: Catalog -> Category (pack) ->
                               Attested Computation (tool); kept apart from the skills tree because
                               each spec forbids the other's frontmatter
"""

import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

OUT = Path(tempfile.mkdtemp(prefix="catalog-out-"))
RESULT = Path("/output/catalog.tar.gz")
INDEX = "index.md"
CONTRIBUTING = "CONTRIBUTING.md"
OKF_DIR = "okf"
ATTESTER = ("meta", "attest-receipt.py")
# The header lines the catalog reads. fragletc ignores what it does not know, so the catalog
# must be the one to refuse a private vocabulary (a '#: category=' nobody consumes).
HEADER_KEYS = {"d", "description", "when", "network", "stdin", "param", "output"}
# The fields of a fraglet-receipt/2, in the order fragletc writes them (pkg/receipt in
# ofthemachine/fraglet). OKF's executor.receipt is the shape of the receipt, so it lists them all.
RECEIPT_FIELDS = ["schema", "fragletc", "procedure", "procedure_hash", "image", "image_digest", "network", "stdin_mode",
                  "params", "inputs", "argv", "env", "memo_key", "started", "finished", "exit_code", "stdout", "outputs"]
MARKETPLACE_NAME = "ofthemachine-tools"
MAX_DESCRIPTION = 1024

COMPAT_BASE = "Requires fragletc and Docker."
COMPAT_HERMETIC = "Hermetic: no network access."
COMPAT_NETWORK = "Network access required."
# The install one-liner as every generated file shows it; `&& fragletc version` is the check that it is on PATH.
INSTALL = "curl -fsSL https://raw.githubusercontent.com/ofthemachine/fraglet/main/install.sh | sh && fragletc version"


def fail(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ----------------------------------------------------------------------------- parse

def read_frontmatter(path: Path) -> Tuple[Dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        fail(f"{path.name}: missing YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        fail(f"{path.name}: frontmatter not closed")
    return (yaml.safe_load(parts[1]) or {}), parts[2]


def procedure_hash(path: Path) -> str:
    """sha256 of the whole file, shebang included -- identical to fragletc --receipt's
    procedure_hash, so a concept and a receipt agree by construction."""
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def parse_tool(path: Path, pack: str) -> Dict[str, Any]:
    """Everything the catalog knows about a tool comes from its header."""
    lines = path.read_text(encoding="utf-8").splitlines()
    image_match = re.search(r"--image[=\s]([^\s]+)", lines[0])
    if not image_match:
        fail(f"{pack}/{path.name}: the shebang must pin an image with --image; every tool runs under fragletc")
    image = image_match.group(1)
    if "@sha256:" not in image:
        fail(f"{pack}/{path.name}: --image must pin a digest (…@sha256:…), not a tag; a tag makes procedure_hash name a script but not what ran")

    ann: Dict[str, List[str]] = {}
    for line in lines:
        if line.startswith("#:") and "=" in line[2:]:
            key, val = line[2:].strip().split("=", 1)
            key = key.strip()
            if key not in HEADER_KEYS:
                fail(f"{pack}/{path.name}: unknown header '#: {key}='; the catalog reads only {sorted(HEADER_KEYS)}")
            ann.setdefault(key, []).append(val.strip())

    params = []
    for decl in ann.get("param", []):
        desc, structural = None, decl
        for marker in (":description=", ":d="):
            i = structural.find(marker)
            if i >= 0:
                desc, structural = structural[i + len(marker):], structural[:i]
                break
        parts = structural.split(":")
        default = next((p.split("=", 1)[1] for p in parts if p.startswith("default=")), None)
        params.append({
            "name": parts[0],
            "type": "file" if "file" in parts else "string",
            "required": "required" in parts and default is None,
            "default": default,
            "description": desc,
        })

    return {
        "pack": pack,
        "stem": path.stem,
        "file": path.name,
        "path": f"{pack}/{path.name}",
        "description": (ann.get("d") or ann.get("description") or [""])[0].strip(),
        "when": " ".join(v for v in ann.get("when", []) if v).strip(),
        "image": image,
        "network": ann.get("network", ["none"])[0],
        "stdin": ann.get("stdin", ["buffer"])[0],
        "params": params,
        "outputs": ann.get("output", []),
        "procedure_hash": procedure_hash(path),
        "_src": path,
    }


def discover_packs(src: Path, vocabulary: Dict[str, str]) -> List[Dict[str, Any]]:
    packs = []
    for d in sorted(p for p in src.iterdir() if p.is_dir() and not p.name.startswith(".")):
        index = d / INDEX
        if not index.exists():
            continue  # not a pack; the compiler never guesses
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", d.name) or len(d.name) > 20:
            fail(f"{d.name}/: pack names are kebab-case, at most 20 characters")
        fm, body = read_frontmatter(index)
        for key in ("title", "description"):
            if not isinstance(fm.get(key), str) or not fm[key].strip():
                fail(f"{d.name}/{INDEX}: frontmatter needs a non-empty '{key}'")
        if "domain" in fm:
            fail(f"{d.name}/{INDEX}: 'domain' is gone; group with 'tags' from the root {INDEX} vocabulary")
        tags = fm.get("tags") or []
        if not isinstance(tags, list) or not tags:
            fail(f"{d.name}/{INDEX}: 'tags' must be a non-empty list")
        for t in tags:
            if t not in vocabulary:
                fail(f"{d.name}/{INDEX}: tag {t!r} is not in the root {INDEX} vocabulary {sorted(vocabulary)}")

        tools = []
        for f in sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith(".") and not p.name.endswith("~")):
            if f.name == INDEX:
                continue
            with f.open("r", encoding="utf-8", errors="ignore") as fh:
                if not fh.readline().startswith("#!"):
                    fail(f"{d.name}/{f.name}: not a tool (no shebang); a pack holds only {INDEX} and tools")
            tools.append(parse_tool(f, d.name))
        if not tools:
            fail(f"{d.name}/: a pack needs at least one tool")
        stems = [t["stem"] for t in tools]
        if len(set(stems)) != len(stems):
            fail(f"{d.name}/: tool stems must be unique within a pack: {sorted(s for s in stems if stems.count(s) > 1)}")

        packs.append({
            "name": d.name,
            "title": fm["title"].strip(),
            "description": fm["description"].strip(),
            "tags": [str(t) for t in tags],
            "tools": tools,
        })
    if not packs:
        fail(f"no packs found (a pack is a directory with an {INDEX} and at least one tool)")
    return packs


# ----------------------------------------------------------------------------- render helpers

def yaml_block(fm: Dict[str, Any]) -> str:
    """Block style, no folding, keys in order: what strictyaml (skills-ref's parser) accepts."""
    return yaml.dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False, width=10**6)


def generated_stamp() -> Dict[str, str]:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    at = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch else datetime.datetime.now(datetime.timezone.utc)
    return {"by": "process:tools/meta/compile-catalog.py", "at": at.replace(microsecond=0).isoformat().replace("+00:00", "Z")}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_tarball(path: Path, entries: List[Path], arcroot: Path) -> None:
    """A reproducible tar.gz: members named relative to arcroot, modes kept, owner and every
    timestamp fixed (SOURCE_DATE_EPOCH, else 0), so the same catalog always yields the same bytes."""
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))

    def anon(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = epoch
        return info
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(path, "wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        for entry in sorted(entries):
            tar.add(entry, arcname=str(entry.relative_to(arcroot)), filter=anon)


def param_line(p: Dict[str, Any]) -> str:
    req = "required" if p["required"] else (f"optional, default `{p['default']}`" if p["default"] is not None else "optional")
    line = f"- `{p['name']}` ({p['type']}, {req})"
    return line + (f" — {p['description']}" if p.get("description") else "")


def stdin_line(mode: str) -> Optional[str]:
    if mode == "buffer":
        return "- stdin (optional) — piped input is read in full and hashed into the run's receipt"
    if mode == "stream":
        return "- stdin (interactive, streamed) — not hashed; such a run has no memo key"
    return None


def usage(tool: Dict[str, Any]) -> str:
    flags = []
    for p in tool["params"]:
        if p["required"]:
            flags.append(f'-p {p["name"]}="<{p["name"]}>"')
        elif p["default"] is not None:
            flags.append(f"[-p {p['name']}={p['default']}]")
        else:
            flags.append(f'[-p {p["name"]}="<{p["name"]}>"]')
    out = f" --output {tool['outputs'][0]}" if tool["outputs"] else ""
    return f"{tool['file']} {' '.join(flags)}{out}".rstrip()


# ----------------------------------------------------------------------------- skills

def pack_summary(pack: Dict[str, Any]) -> str:
    """The pack's description plus its tool names as keywords: what llms.txt lists."""
    return f"{pack['description'].rstrip('.')}. Tools: {', '.join(t['stem'] for t in pack['tools'])}."


def pack_description(pack: Dict[str, Any]) -> str:
    """The skill description: the spec wants what it does and when to use it."""
    desc = f"{pack_summary(pack)} Use when a request needs any of these; each tool's own trigger is in SKILL.md."
    if len(desc) > MAX_DESCRIPTION:
        fail(f"{pack['name']}: skill description is {len(desc)} chars (max {MAX_DESCRIPTION}); the pack is too big -- split it by subject")
    return desc


def render_skill(pack: Dict[str, Any]) -> str:
    network = any(t["network"] != "none" for t in pack["tools"])
    fm = {
        "name": pack["name"],
        "description": pack_description(pack),
        "compatibility": f"{COMPAT_BASE} {COMPAT_NETWORK if network else COMPAT_HERMETIC}",
        **({"license": pack["_license"]} if pack.get("_license") else {}),
        "metadata": {
            "tags": ", ".join(pack["tags"]),
            "tools": ", ".join(t["file"] for t in pack["tools"]),
        },
    }
    sections = []
    for t in pack["tools"]:
        lines = [param_line(p) for p in t["params"]] or ["- none"]
        if stdin_line(t["stdin"]):
            lines.append(stdin_line(t["stdin"]))
        outputs = "\n".join(f"- `{o}` — copy out with `--output {o}[=<host path>]`" for o in t["outputs"]) or "- stdout"
        reach = ("hermetic — `network=none`; a run is a pure function of its inputs and safe to memoize"
                 if t["network"] == "none" else
                 "network required — output depends on live external state; do not cache indefinitely")
        sections.append(f"""### `{t['file']}`

{t['description']}

{t['when']}

```sh
<skill-dir>/{usage(t)}
```

Parameters:
{chr(10).join(lines)}

Outputs:
{outputs}

Runs in `{t['image']}`; {reach}.
""")
    first = pack["tools"][0]["file"]
    body = f"""# {pack['title']}

{pack['description']}

Every tool below is one executable file beside this `SKILL.md`, in the directory the commands below call `<skill-dir>`. Run it directly. Two host requirements: [`fragletc`](https://github.com/ofthemachine/fraglet) (`{INSTALL}`) and Docker; the image, parameters, outputs and network reach are declared in the file itself. Before running a tool, print its contract:

```sh
<skill-dir>/{first} --fraglet-help
```

Parameters are passed as `-p name=value` (a `file` parameter takes a host path); declared outputs are copied out with `--output <name>[=<host path>]`. A missing required parameter fails host-side with exit 2 before any container starts; otherwise the tool's own exit code is the run's. A declared output not named with `--output` is produced and discarded (a stderr note says what you could have copied). Add `--receipt run.json` (or set `FRAGLETC_RECEIPT_DIR`) to record the run: the receipt carries the tool's `procedure_hash`, image digest, parameters, and every input and output by content hash, and `meta/attest-receipt.py` can verify it later without re-running anything.

## Tools

{chr(10).join(sections)}"""
    return f"---\n{yaml_block(fm)}---\n\n{body}"


def render_plugin(pack: Dict[str, Any], version: str) -> Dict[str, Any]:
    return {
        "name": pack["name"],
        "version": version,
        "description": pack["description"],
        "author": {"name": "ofthemachine"},
        "keywords": pack["tags"] + [t["stem"] for t in pack["tools"]],
        **({"license": pack["_license"]} if pack.get("_license") else {}),
        "skills": ["./"],
    }


def render_marketplace(packs: List[Dict[str, Any]], catalog: Dict[str, Any], version: str) -> Dict[str, Any]:
    return {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "ofthemachine"},
        "version": version,
        "description": catalog["description"],
        **({"license": catalog["license"]} if catalog.get("license") else {}),
        "renames": {r["from"]: r["to"] for r in catalog["renames"] if "/" not in r["from"]},
        "plugins": [
            {
                "name": p["name"],
                "source": f"./{p['name']}",
                "description": p["description"],
                "version": version,
                "tags": p["tags"],
                **({"license": catalog["license"]} if catalog.get("license") else {}),
                "skills": ["./"],
            }
            for p in packs
        ],
    }


# ----------------------------------------------------------------------------- llms.txt

def render_llms(packs: List[Dict[str, Any]], catalog: Dict[str, Any], base: str, contributing: bool) -> str:
    lines = [
        f"# {catalog['title']}",
        "",
        f"> {catalog['description']} Each pack below is one Agent Skill: a SKILL.md listing its tools, with the tools beside it. A tool is a single file that runs in a pinned container via fragletc (https://github.com/ofthemachine/fraglet; install with `{INSTALL}`) and Docker; `<tool> --fraglet-help` prints its contract, `--receipt` records a run. The whole catalog is also published as catalog.tar.gz beside this file.",
        "",
        # Commands first: an agent runs what is runnable and guesses at what is elided, so the host is
        # literal and the only variables are the two it must choose.
        "## Install",
        "",
        "```sh",
        INSTALL,
        f"curl -fsSL {base}/<pack>.tar.gz | tar xz -C <skills dir>   # -> <skills dir>/<pack>/SKILL.md, wherever your harness loads skills from",
        "sha256sum <skills dir>/<pack>/*   # each tool's must equal its procedure_hash in manifest.json",
        "```",
        "",
        "## Packs",
        "",
    ]
    lines += [f"- [{p['name']}]({p['name']}/SKILL.md): {pack_summary(p)}" for p in packs]
    lines += [
        "",
        "## Optional",
        "",
        "- [llms-full.txt](llms-full.txt): every pack's SKILL.md, concatenated",
        "- [manifest.json](manifest.json): every tool's contract and procedure_hash, as JSON",
        *(["- [CONTRIBUTING.md](CONTRIBUTING.md): how to write a new tool -- clone a sibling, header grammar, verification protocol"] if contributing else []),
        "- [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json): the packs as a Claude Code plugin marketplace",
        f"- [{OKF_DIR}/{INDEX}]({OKF_DIR}/{INDEX}): the same catalog as an Open Knowledge Format bundle",
        "",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- OKF

def okf_frontmatter(fm: Dict[str, Any]) -> str:
    return yaml.dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False, width=10**6)


def write_okf_index(path: Path, fm: Dict[str, Any], heading: str, intro: str, entries: List[Tuple[str, str, str]]) -> None:
    lines = [f"# {heading}", "", intro, ""] + [f"- [{label}]({target}) — {desc}" for target, label, desc in entries]
    write(path, f"---\n{okf_frontmatter(fm)}---\n\n" + "\n".join(lines) + "\n")


def okf_computation(t: Dict[str, Any], tags: List[str], generated: Dict[str, str], base: str, license_: str = "") -> str:
    """An 'Attested Computation' concept at okf/<pack>/<stem>.md.

    Locators are canonical URLs, never paths out of the bundle: the OKF tree must stay separate
    from the skills tree (each spec forbids the other's frontmatter), so nothing in it may point
    across with '../'. A URL says where; procedure_hash says what it must hash to -- the same
    pairing a receipt records. Links between concepts stay relative because they stay inside."""
    hermetic = t["network"] == "none"
    script = f"{base}/{t['path']}"
    skill = f"{base}/{t['pack']}/SKILL.md"
    attester = f"{base}/{'/'.join(ATTESTER)}"
    fm: Dict[str, Any] = {
        "type": "Attested Computation",
        "title": t["stem"],
        "identifier": t["path"].rsplit(".", 1)[0],
        "description": t["description"],
        "pack": t["pack"],
        "tags": list(tags),
        "runtime": "fragletc",
        "image": t["image"],
        "network": t["network"],
        "stdin": t["stdin"],
        "execution_class": "hermetic" if hermetic else "environmental",
        "procedure_hash": t["procedure_hash"],
        "parameters": [
            {"name": p["name"], "type": p["type"], "required": bool(p["required"]),
             **({"default": p["default"]} if p.get("default") is not None else {}),
             **({"description": p["description"]} if p.get("description") else {})}
            for p in t["params"]
        ],
        "computation": script,
        "executor": {
            "resource": "https://github.com/ofthemachine/fraglet",
            "receipt": RECEIPT_FIELDS,
            "format": "fraglet-receipt/2 (fragletc --receipt <path>, or FRAGLETC_RECEIPT_DIR)",
        },
        "attester": {
            "resource": attester,
            "method": "deterministic, no re-execution: procedure_hash equals sha256 of computation; memo_key recomputes "
                      "from the receipt's own fields; claimed params and any artifact hash match the receipt",
        },
        "generated": generated,
    }
    if t["outputs"]:
        fm["outputs"] = list(t["outputs"])
    if license_:
        fm["license"] = license_

    params_md = "\n".join(param_line(p) for p in t["params"]) or "- none"
    if stdin_line(t["stdin"]):
        params_md += "\n" + stdin_line(t["stdin"])
    outputs_md = "\n".join(f"- `{o}` (declared file under /output)" for o in t["outputs"]) or "- stdout (the anonymous result)"
    reach = (
        "Hermetic: no network, so `memo_key` also fully determines the outputs — a re-run with the same inputs "
        "must reproduce them, which makes results from this tool safely memoizable."
        if hermetic else
        "Environmental: the tool reaches the network, so outputs depend on state outside its inputs; the receipt "
        "records exactly what ran and what came out and makes no reproduction claim."
    )
    body = f"""# {t['stem']}

{t['description']}

{t['when']}

# Schema

## Parameters
{params_md}

## Outputs
{outputs_md}

# Execution

The computation is [`{t['path']}`]({script}) (frontmatter `computation`; in `catalog.tar.gz` the same file sits at `{t['path']}` beside this bundle), run by `fragletc` in `{t['image']}` with network `{t['network']}`. Its identity is `procedure_hash` = sha256 of that file, shebang included — the same value every receipt records. Parameters are passed as `-p name=value`; `--receipt run.json` (or `FRAGLETC_RECEIPT_DIR`) writes the receipt, a `fraglet-receipt/2` JSON document with the fields listed under `executor.receipt`.

# Attestation

A run's receipt is attested with [`meta/attest-receipt.py`]({attester}): the computation that ran is this script (`procedure_hash`), the receipt is internally consistent (`memo_key` recomputes from its own fields), the claimed parameters are the ones that ran, and an artifact claimed as an output hashes to what the receipt recorded. No re-execution: attestation is provenance fidelity, not reproduction.

{reach}

Skill: [SKILL.md]({skill})
"""
    return f"---\n{okf_frontmatter(fm)}---\n\n{body}"


# ----------------------------------------------------------------------------- main

def unpack(archive: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="catalog-src-"))
    try:
        with tarfile.open(archive, "r:*") as tar:
            for m in tar.getmembers():
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    fail(f"unsafe archive member {m.name!r}")
                if not os.path.basename(m.name).startswith("._"):
                    tar.extract(m, root)
    except tarfile.TarError as e:
        fail(f"cannot unpack archive: {e}")
    # Tolerate one wrapping directory (tar czf src.tar.gz <dir>) as well as a flat archive.
    entries = [p for p in root.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir() and not (root / INDEX).exists():
        return entries[0]
    return root


def main() -> None:
    base = "https://" + os.environ["HOST"].strip().strip("/")
    src = unpack(os.environ["ARCHIVE"])
    if not (src / INDEX).exists():
        fail(f"the archive has no top-level {INDEX} (the Catalog concept with the tag vocabulary)")
    catalog_fm, _ = read_frontmatter(src / INDEX)
    vocabulary = catalog_fm.get("tags")
    if not isinstance(vocabulary, dict) or not vocabulary:
        fail(f"{INDEX}: 'tags' must be a mapping of tag -> one-line description (the closed vocabulary)")
    version = str(catalog_fm.get("version") or "0.0.0")
    renames = catalog_fm.get("renames") or []
    if not isinstance(renames, list) or any(not isinstance(r, dict) or set(r) < {"from", "to", "since"} for r in renames):
        fail(f"{INDEX}: 'renames' must be a list of {{from, to, since}}")
    catalog = {"title": str(catalog_fm.get("title") or "tools"), "description": str(catalog_fm.get("description") or "").strip(),
               "license": str(catalog_fm.get("license") or "").strip(), "renames": renames}

    packs = discover_packs(src, {str(k): str(v) for k, v in vocabulary.items()})
    for p in packs:
        p["_license"] = catalog["license"]
    generated = generated_stamp()
    OUT.mkdir(parents=True, exist_ok=True)

    # Skills + plugins: the compiled pack is the source pack plus generated files.
    skills_text = []
    for p in packs:
        pack_dir = OUT / p["name"]
        pack_dir.mkdir(parents=True, exist_ok=True)
        for t in p["tools"]:
            shutil.copy2(t["_src"], pack_dir / t["file"])
        skill = render_skill(p)
        write(pack_dir / "SKILL.md", skill)
        skills_text.append(skill)
        write(pack_dir / ".claude-plugin" / "plugin.json", json.dumps(render_plugin(p, version), indent=2) + "\n")
        # The pack as one file: `curl … <pack>.tar.gz | tar xz -C <skills dir>` installs it anywhere.
        write_tarball(OUT / f"{p['name']}.tar.gz", [pack_dir], OUT)
    write(OUT / ".claude-plugin" / "marketplace.json", json.dumps(render_marketplace(packs, catalog, version), indent=2) + "\n")

    # CONTRIBUTING.md, when the source carries it, so an agent arriving at llms.txt can find how to
    # author a tool; its sibling references (words/palindrome.py) resolve at the same paths here.
    contributing = (src / CONTRIBUTING).exists()
    if contributing:
        shutil.copy2(src / CONTRIBUTING, OUT / CONTRIBUTING)

    # llms.txt: install -> packs -> SKILL.md -> tool.
    write(OUT / "llms.txt", render_llms(packs, catalog, base, contributing))
    write(OUT / "llms-full.txt", "\n\n".join(skills_text) + "\n")

    # OKF bundle.
    okf = OUT / OKF_DIR
    for p in packs:
        for t in p["tools"]:
            write(okf / p["name"] / f"{t['stem']}.md", okf_computation(t, p["tags"], generated, base, catalog.get("license", "")))
        write_okf_index(
            okf / p["name"] / INDEX,
            {"type": "Category", "title": p["title"], "description": p["description"], "tags": p["tags"], "generated": generated},
            p["title"], p["description"],
            [(f"{t['stem']}.md", t["stem"], t["description"]) for t in p["tools"]],
        )
    write_okf_index(
        okf / INDEX,
        {"type": "Catalog", "title": catalog["title"], "description": catalog["description"], "version": version,
         "tags": vocabulary, "generated": generated},
        catalog["title"],
        f"Every pack as a Category, every tool as an Attested Computation. Computations and the attester are located by canonical URL under {base}/ and pinned by `procedure_hash`; in `catalog.tar.gz` the same files sit one level above this bundle at the URL's path.",
        [(f"{p['name']}/{INDEX}", p["title"], f"{len(p['tools'])} tools — {p['description']}") for p in packs],
    )

    # manifest.json: the structured view.
    manifest = {
        "base_url": base,
        "title": catalog["title"],
        "description": catalog["description"],
        **({"license": catalog["license"]} if catalog["license"] else {}),
        "version": version,
        "renames": renames,
        "generated": generated,
        "tags": vocabulary,
        "packs": [{k: p[k] for k in ("name", "title", "description", "tags")} | {"tools": [t["stem"] for t in p["tools"]]} for p in packs],
        "tools": [{k: v for k, v in t.items() if not k.startswith("_")} | {"id": t["path"].rsplit(".", 1)[0], "url": f"{base}/{t['path']}", "usage": usage(t)}
                  for p in packs for t in p["tools"]],
    }
    write(OUT / "manifest.json", json.dumps(manifest, indent=2) + "\n")

    # The archive is the catalog root: unpack it anywhere and llms.txt sits at the top.
    write_tarball(RESULT, list(OUT.iterdir()), OUT)
    n_tools = sum(len(p["tools"]) for p in packs)
    print(f"catalog v{version}: {len(packs)} packs, {n_tools} tools -> skills, plugins, llms.txt, manifest.json, {OKF_DIR}/")


if __name__ == "__main__":
    main()
