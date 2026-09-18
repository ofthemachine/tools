# Contributing a tool

A tool is a fraglet: a single-purpose, executable script with a container shebang and declared input/output contracts. This catalog holds level-0 tools only -- one file each, nothing authored outside the file. Composite skills that drive these tools live in `ofthemachine/skills`, not here.

A tool PR touches one file: `<pack>/<stem>.<ext>`. A new pack adds `<pack>/index.md` (title, description, `tags` from the vocabulary in the root `index.md`) and its first tool. Read the root `index.md` for the taxonomy and growth rules before choosing a pack name. Review is `make build` -- `fragletc lint --strict`, the compiler, and the validator; CI runs the same.

## Clone a Sibling (Do Not Start From Blank)

Match the desired I/O shape and copy that script — shebang, header, body shape — then edit:

| Desired Input/Output Shape | Existing Sibling to Clone |
| :--- | :--- |
| **String Parameter** (e.g. text, word, regex) | `words/palindrome.py` |
| **No-Param External API** (fetch, print) | `trivia/advice.py` |
| **External API + String Params** | `weather/current.py` |
| **File XOR Text** (file mount and/or inline string) | `data/jq-slice.py` |
| **Single Host File Mount** (e.g. source code, image) | `code/symbol-outline.py` |
| **Archive Bundle Input** (multi-file, assets) | `doc/markdowns-to-pdf.py` |
| **Declared File Output** (e.g. image, PDF) | `meme/n-line.sh` |
| **Two Host File Mounts** (comparison, merge) | `image/diff.py` |

**Trigger (one line):** `#: when=Use when ...` — the situations an agent should reach for this tool, in the words a request would use. `d=` is what the tool does; `when=` is when to use it. Both land verbatim in the pack's `SKILL.md`, so they are the sentences an agent matches a request against.

**Stdin (always declare it):** `#: stdin=none` for a tool that never reads stdin (most of the catalog); `#: stdin=buffer` for piped input (read to EOF, hashed into the receipt so the memo key covers it); `#: stdin=stream` only for a genuinely interactive program — such runs get no memo key. Undeclared means `buffer`.

**Network (one line):** `#: network=required` if the tool fetches or calls an API; `#: network=none` if it is pure computation. When `network=none` is declared, `fragletc` enforces isolation with `docker run --network none`.

**Header vocabulary is closed:** the build reads the directives fragletc defines — `d=`, `when=`, `network=`, `stdin=`, `param=`, `output=` — and refuses any other `#:` key. New directives are a fragletc change first, never a catalog convention. `--image` must pin a digest (`@sha256:`); a tag is refused.

**Form of `d=`:** a noun phrase naming the result for a tool that returns a value ("The Moon's phase on a given date…"), an imperative for a transformation ("Render one Markdown file to PDF…"). Say what distinguishes it from its siblings, naming them by `<pack>/<stem>`; when a sibling is renamed, grep for it.

## Authoring & Verification Protocol

```
1. Scaffold: Clone sibling into <pack>/<tool-name>.<ext>
   (a new pack also needs <pack>/index.md: type: Category, title, description, tags)
2. Permissions: chmod +x <pack>/<tool-name>.<ext>
3. Fail-Fast Test: Run without parameters; verify exit code 2 and parameter table
4. Help Inspection: Run with --fraglet-help; verify description and options
5. Happy-Path Test: Run with required -p flags and verify output
6. Lint: fragletc lint --strict <pack>/<tool-name>.<ext>
7. Catalog Sync: make build   (lints every pack first)
```

### Verification Checklist

- [ ] Script is executable (`chmod +x`).
- [ ] Trigger declared: `#: when=Use when ...` names the requests this tool answers (no generic "use when the user requests <name>").
- [ ] Network reach declared: `#: network=required` if reaching the network, or `#: network=none` for enforced hermetic isolation.
- [ ] Missing required parameters trigger instant host-side failure (exit code 2).
- [ ] Declared `default=` values are not re-encoded in the script body (header is SSOT).
- [ ] `--fraglet-help` outputs clean documentation (including param `description=` / `d=` when set).
- [ ] `fragletc lint --strict` reports the file clean (see Parameter Conformance below).
- [ ] Script writes file outputs strictly under `/output/` (matching declared `#: output=`).
- [ ] Running `make build` compiles `catalog/` and passes validation with zero errors; the new tool appears in `catalog/<pack>/SKILL.md` and `catalog/llms.txt`.

---

## Parameter Conformance (`fragletc lint`)

fragletc owns the header grammar, so fragletc lints it — `fragletc lint --strict <script>` is the single source of truth and `make build` refuses a tree that fails it. The rules, in the order you will hit them:

- **Every `param=` has a `:d=`/`:description=`, and it is the last modifier.** The prose runs to end of token, so anything after it (`:default=`, `:file`) is silently swallowed into the description.
- **Only `required`, `file`, `default=`, `envvar=`, `d=`/`description=`.** A typo (`requried`) is a no-op to fragletc; bare `optional` is redundant — omit it.
- **`required` and `default=` never together.** `default=` silently exempts `required`.
- **Alias is `[a-z][a-z0-9_]*`** (it becomes the env var); a dotted suffix (`source.tex`) only with `:file`.
- **The body reads the env var** (`ALIAS` uppercased, or `envvar=`) for every declared param. Lint infers nothing else from the body — so the rule it cannot see is on you: **never re-encode a declared `default=`** (`os.environ.get("X", "5")`, `${X:-5}`); the header is the source of truth.
- **`network=none` or `network=required`** is declared; tool-level `d=` and `when=` lines exist.

Conformant — `web/screenshot.py`:

```python
#: network=required
#: param=url:required:d=Page URL to capture
#: param=headers:d=JSON object of extra HTTP headers (e.g. Authorization)
#: param=settle_ms:default=2000:description=Extra wait after page load for async JS content
settle_ms = int(os.environ["SETTLE_MS"])      # default injected by fragletc; no fallback here
```

Non-conformant — what `news/rss-headlines.py` looked like before:

```python
#: param=feed:required                        # no description
#: param=count:optional                       # optional does nothing; the real default hides below
count = int(os.environ.get("COUNT") or 5)     # default re-encoded in the body (lint can't see this; the checklist can)
```

```
$ fragletc lint news/rss-headlines.py
news/rss-headlines.py: warning: network-missing: no #: network= line; declare network=none (enforced hermetic) or network=required
news/rss-headlines.py:3: warning: param-no-description: param=feed has no description; add :d=<what the caller should pass>
news/rss-headlines.py:4: warning: param-no-description: param=count has no description; add :d=<what the caller should pass>
news/rss-headlines.py:4: warning: param-optional-redundant: param=count: optional is the default and does nothing; omit it
```

Fix: `#: param=count:default=5:d=Number of headlines to print` and `count = int(os.environ["COUNT"])`.

---

## When Parroting Is Not Enough

Read the rest of this document only when the sibling table has no matching row, or when a clone fails for contract reasons (mounts, outputs, defaults, hermeticity).

### Core Constraints (Still Apply)

- **Pin on creation, never churn:** pin the shebang to the latest digest that provides the needed libraries. Never cascade repins to working siblings.
- **Zero runtime installs:** never `pip install` / `apk add` / `apt-get` in the script body. Missing libs → update the container in `ofthemachine/containers`.
- **Any language:** the shebang chooses the image, and any fraglet-enabled container works -- the 90+ `100hellos/<lang>` images or the purpose-built `ofthemachine/<image>` ones (`python3`, `headless-browser`, `latex`, `meme`, `home-automation`, `3d-printing`, ...). `words/wordle-solve.java` runs on `100hellos/java`. Pin by digest.

### Directive Specification Format

Declare metadata and contracts immediately below the shebang with `#: ` lines:

```python
#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:<the digest of the sibling you cloned>
#: d=One-sentence capability pitch describing what the tool computes or transforms.
#: when=Use when the user asks for <the requests this answers>, or <the situation a workflow hits>.
#: network=none
#: stdin=none
#: param=input_text:required:d=Raw text to transform
#: param=mode:default=fast:description=fast or thorough
#: param=source_file:required:file
#: output=result.json
```

- `d=<description>` (tool-level, alone on its `#:` line): Concise capability summary. Avoid meta-phrasing like "this script".
- `when=<trigger>` (tool-level, alone on its `#:` line): When an agent should use it, phrased as the requests it answers. Lint warns (`when-missing`) without it; the catalog build is strict.
- `network=none` / `network=required`: Egress declaration. `network=none` → `fragletc` adds `--network none`.
- `stdin=none` / `stdin=buffer` / `stdin=stream`: stdin stance; undeclared means `buffer`. `none` asserts the tool never reads it, `buffer` for piped input (hashed), `stream` for interactive (no memo key).
- `param=<alias>:required`: Host-side failure (exit 2) if `-p <alias>=...` is missing.
- `param=<alias>:default=<value>`: Injected into the container env when `-p` is omitted. Explicit `-p` (including empty) wins. Also exempts `required`.
- `param=<alias>:…:description=<prose>` or `:d=<prose>`: Per-param help text (must be last modifier; spaces OK). Surfaces in `--fraglet-help`.
- `param=<alias>:file`: Mounts the host file read-only at `/input/<alias>`.
- `output=<relpath>`: Script writes `/output/<relpath>`.

Access parameters via environment variables (e.g. `os.environ["INPUT_TEXT"]` or `$INPUT_TEXT`). Do not re-encode `default=` in the body — the header is the source of truth.

### File Input Mounts (`:file`) and Extensions

`param=<alias>:file` mounts the caller's host file read-only at `/input/<alias>`. The container never sees the host path layout.

- **Content-driven tools** (JSON, Markdown, images sniffing magic bytes): `param=input_file:file` and read `/input/input_file`.
- **Extension-dependent tools** (LaTeX, compilers): put the extension in the alias — `#: param=source.tex:required:file` mounts at `/input/source.tex`.
- **Polyglot open-ended formats** (e.g. `symbol-outline.py`, 140+ languages): optional companion param (`file_path`) so the script can symlink `/tmp/input.<ext>`.

### The Closed Input Contract

A fraglet execution is identified by the pinned image digest, the script body, declared parameters, and declared `:file` mount contents. That closure makes runs memoizable and distributable.

**No directory mounts (by design).** Narrow to a single file, accept a tarball/zip as a file param (see `doc/markdowns-to-pdf.py`), or accept the capability is out of scope. A tool that cannot be expressed as a fraglet does not belong in this catalog; there are no exceptions.

**Network reach.** `#: network=none` asserts hermetic execution and is enforced host-side. `#: network=required` marks live external state; do not memoize indefinitely. Explicit `fragletc --network` overrides the header. The compiler surfaces `network:` in the pack's SKILL.md and derives the OKF concept's `execution_class` from it: a hermetic tool's `fragletc --receipt` memo key fully determines its outputs, so keep `network=none` honest — a hermetic tool that secretly reads the clock or the network breaks that promise.

Verify hermetic tools:
```bash
./<pack>/<tool>.py -p <required-params>   # --network none if declared
fragletc --network none ./<pack>/<tool>.py -p <required-params>
```

### Output File Contracts (`#: output=`)

Write artifacts only under `/output/<relpath>`.

**Single output** — bare destination is enough:
```bash
./render-report.py -p title="Q3" --output ./final-report.pdf
```

**Multiple outputs** — explicit `--output <relpath>=<hostdest>` pairs (or `--output <relpath>` → `./<relpath>`). Unrequested declared outputs are reported as discarded on stderr.

**Dynamic runtime filenames** — `--output-dir=./build-artifacts` copies everything under `/output`. Mutually exclusive with `--output`.
