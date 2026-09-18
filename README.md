# tools

A catalog of **level-0 tools** for AI agents: single-file [fraglets](https://github.com/ofthemachine/fraglet) — `#!/usr/bin/env -S fragletc --image=…` scripts that run in pinned containers on demand — organised into **packs** by subject and published as one [Agent Skill](https://agentskills.io) per pack. A tool can be written in any language that has a fraglet-enabled container: the 90+ [100hellos](https://github.com/ofthemachine/100hellos) language images or the purpose-built [ofthemachine](https://github.com/ofthemachine/containers) ones (python3, headless-browser, latex, meme, home-automation, 3d-printing, …). No local toolchains or language runtimes are ever required: **Docker** is the only host runtime dependency, and `fragletc` the only host binary.

Nothing about a tool lives outside its file. Everything else in this repository — the skills, the `llms.txt`, the Claude Code plugins, the Open Knowledge Format bundle — is compiled from the tools' own headers.

---

## Install `fragletc`

```sh
curl -fsSL https://raw.githubusercontent.com/ofthemachine/fraglet/main/install.sh | sh     # installs to ~/.local/bin
# or: FRAGLETC_INSTALL_DIR=/usr/local/bin curl -fsSL … | sh
# or: go install github.com/ofthemachine/fraglet/cmd/fragletc@latest
fragletc version
```

Then any tool runs from the repository root, no build needed:

```sh
./web/readable-markdown.py -p url="https://example.com" --output example.md
./token/counter.py -p text="The quick brown fox jumps over the lazy dog."
./meme/n-line.sh -p template=drake -p lines="Bloated context|Polyglot symbol outline" --output meme.png
./words/wordle-solve.java -p clues="crane:XYXXG|mould:XXXXX"
./math/is-prime.py -p n=7 --receipt run.json        # a receipt for the run, attestable later
./web/search.py --fraglet-help                      # any tool prints its own contract
```

---

## Layout

```
tools/                        github.com/ofthemachine/tools  ==  tools.ofthemachine.com
  index.md                    the Catalog: tag vocabulary, taxonomy, growth rules
  CONTRIBUTING.md             how to write a tool
  <pack>/index.md             the pack: title, description, tags
  <pack>/<stem>.<ext>         tools -- nothing else is in a pack
  meta/compile-catalog.py     the build, itself a tool: src.tar.gz in, catalog.tar.gz out
  meta/validate-catalog.py    the validator, itself a tool: catalog.tar.gz in, verdict out
  meta/attest-receipt.py      attests a fragletc receipt against the tool that ran
  meta/receipt-ledger.py      folds receipts into a ledger
  meta/site.py                the website, itself a tool: catalog.tar.gz in, site.tar.gz out
  catalog/  site/             build outputs (gitignored) -- see Projections
```

A **pack** is any root directory with an `index.md` and at least one shebang file. That is the whole rule; the build never needs a list. Today's packs:

| pack | tools | tags |
|---|---|---|
| `astro` | moon-phase, sun-times (computed, hermetic) | world |
| `code` | symbol-outline (Universal Ctags, 140+ languages) | engineering |
| `data` | jq-slice | engineering, computation |
| `diagram` | graphviz (dot, neato, fdp, circo, twopi, sfdp) | media |
| `doc` | markdown-to-pdf, markdowns-to-pdf, bundle-to-pdf, latex-to-pdf, extract-text | documents |
| `image` | transform (Pillow), diff | media |
| `math` | is-prime, fibonacci | computation |
| `meme` | explore, n-line (meme-cli) | media |
| `meta` | compile-catalog, validate-catalog, site, attest-receipt, receipt-ledger | engineering |
| `net` | my-ip, geo-ip | internet |
| `news` | world-headline(s), rss-headlines, archive-lookup | world |
| `token` | counter, chunk (tiktoken) | engineering |
| `trivia` | advice, cat-fact, random-joke, on-this-day | world |
| `weather` | current (wttr.in), forecast (Open-Meteo) | world |
| `web` | search, readable-markdown, url-metadata, screenshot, pdf-of-url | internet, documents |
| `words` | palindrome, rot13, wordle-solve | computation |

### Taxonomy

Two axes; a path segment is identity, a tag is grouping. A pack name is a **subject noun** — what its tools act on or produce — never a verb, runtime, or container. Tags are criteria from the closed vocabulary in the root `index.md` (a pack carries every tag whose criterion its tools meet), and the build refuses any other. The growth rules (when a pack splits, where a one-tool pack is allowed, what counts as a breaking rename, when tags become facets) are in `index.md` too; they are the contract for contributors, so they live with the vocabulary they govern.

### What this repository does not hold

Composite skills (prose that sequences tools with model judgement) and behavioral directives are a separate problem with a separate home, `ofthemachine/skills`. They depend on this catalog — vendoring tools by path and `procedure_hash` from `manifest.json` — and never the reverse.

---

## Projections

`make build` lints every pack with `fragletc lint --strict`, compiles them with `meta/compile-catalog.py`, validates the result with `meta/validate-catalog.py` (which runs [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref), the spec's own validator, plus the catalog rules), and unpacks `catalog.tar.gz` into `catalog/`. One parse of the headers, several renders:

| in `catalog/` | for | what |
|---|---|---|
| `<pack>/SKILL.md` + the tools | every Agent Skills harness | **the pack is the skill.** `name` is the pack; the body is a table of its tools — `d=`, `when=`, parameters, outputs, image, network reach — and the tools sit beside it byte-identical, so `web/search.py` is the same path in the repo, in the catalog, in `~/.claude/skills/web/`, and on the web |
| `<pack>/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude Code | one plugin per pack |
| `llms.txt`, `llms-full.txt` | any agent with HTTP | [llmstxt.org](https://llmstxt.org): packs → `SKILL.md` → tool. Two fetches from `llms.txt` to a runnable, pinned, receipt-emitting tool |
| `manifest.json` | tooling | every tool's typed contract and `procedure_hash`; every pack's tags |
| `okf/` | knowledge consumers | the same catalog as an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundle (below) |
| `site/` (from `make site`) | humans, at [tools.ofthemachine.com](https://tools.ofthemachine.com) | the catalog served verbatim plus an HTML layer beside it: an explorer of every tool (search, tag and pack filters, grid/table, dark/light), a page per pack, a page per tool with its contract, provenance, a curl one-liner and its source. `meta/site.py`, catalog.tar.gz in, site.tar.gz out; relative links, so it also opens from `file://` |

Why one skill per pack and not per tool: a harness loads every installed skill's name and description at startup (~100 tokens each), so a catalog of hundreds of tools as hundreds of skills spends tens of thousands of tokens before an agent reads the request. The pack description carries the tool names as keywords; the pack body carries each tool's trigger; `--fraglet-help` carries the contract. That is the spec's own metadata → instructions → resources ladder.

### Using the catalog

| harness | path |
|---|---|
| Claude Code | `make link-skills` symlinks every `catalog/<pack>` into `~/.claude/skills/<pack>`; or `make build && claude plugin marketplace add "$PWD/catalog" && claude plugin install web@ofthemachine-tools` |
| any agentskills.io harness | copy or symlink `catalog/<pack>/` — self-contained by construction |
| any agent over HTTP | read `llms.txt`, follow a pack to its `SKILL.md`, `curl -O` the tool; or fetch `catalog.tar.gz` whole |
| a composite skill | `manifest.json` → the tool's path and `procedure_hash`; vendor the file |

---

## Open Knowledge Format: the same catalog as knowledge

[Agent Skills](https://agentskills.io) is a procedure format: a `SKILL.md` says how to *do* something. [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (v0.2) is a knowledge format: a directory of markdown concepts linked into a graph. They are complementary, and each forbids the other's frontmatter, so the build emits both from the same headers into separate trees:

| here | OKF concept in `catalog/okf/` | carries |
|---|---|---|
| tool | `type: Attested Computation` | `runtime: fragletc`, pinned `image`, typed `parameters`, `network` / `execution_class`, `procedure_hash`, `executor` (the receipt) and `attester` (`meta/attest-receipt.py`) |
| pack | `type: Category` (`index.md`) | title, description, tags, links to its computations |
| catalog | `type: Catalog` (`index.md`) | the tag vocabulary, links to every pack |

A fraglet *is* an attested computation, in OKF's sense: a sanctioned computation with declared parameter holes that an agent may fill but not edit. Attestation lets a consumer confirm mechanically that a value came from the sanctioned computation with the claimed parameters:

- **executor** — `fragletc`. `--receipt run.json` (or `FRAGLETC_RECEIPT_DIR=<dir>` for a whole session) writes the evidence for one run: `procedure_hash` (sha256 of the script file, image pin included), image digest, params, inputs (stdin, `:file` params) and outputs (every file under `/output`, or stdout) by content hash, exit code, and a `memo_key` computed by fragletc's documented formula. The concept's `procedure_hash` is computed the same way, so a receipt and the concept describing it agree by construction.
- **attester** — `meta/attest-receipt.py`, deterministic and offline: the computation that ran is the sanctioned script, the receipt's `memo_key` recomputes from its own fields (an edited receipt fails), claimed params match, the run succeeded, and an artifact claimed as an output hashes to what the receipt recorded. No re-execution — attestation is provenance fidelity, not reproduction. Hermeticity (`#: network=none`) is the separate, related property that makes results memoizable.
- **consumer** — any skill that publishes results, such as the Daily Fraglet in `ofthemachine/skills`: every tool run behind an edition leaves a receipt, the receipts ship with the result, and each figure is attested before printing. Receipts travel with the *result*, never in the catalog — as the spec intends.

---

## Two shapes of tool

**Shaped tools** — e.g. `meme/n-line.sh`, `weather/current.py`, `doc/markdown-to-pdf.py`. Fixed `#: param=` names and a fixed `#: output=` declaration when file outputs exist. A stable code hash plus a closed, declared set of named inputs makes a script deterministic, memoizable, and composable.

**Generic passthrough** — e.g. `meme/explore.sh`. No declared params (`meme-cli "$@"`). For discovery (`search`/`show`/`list`) and one-offs.

---

## Commands

```bash
make build         # lint every pack, compile catalog.tar.gz, validate it, unpack into catalog/
make lint          # fragletc lint --strict over every pack
make validate      # re-validate an unpacked catalog/
make site          # build, then render the website from the validated catalog.tar.gz into site/
make serve         # site, then serve site/ with nginx on http://localhost:8080 (docker; PORT=n to change)
make link-skills   # build, then symlink catalog/<pack> into ~/.claude/skills/<pack>
make clean         # remove catalog/, site/ and their archives
```

## Publishing

`.github/workflows/build.yml` runs `make build` on every push and pull request: that is the whole review of a tool. `.github/workflows/pages.yml` runs `make site` on `main` and deploys `site/` to GitHub Pages as tools.ofthemachine.com — so the published site is produced by the same fraglets, in the same images by digest, as a local build. The `CNAME` file inside the site comes from `meta/site.py`'s `host` parameter.
