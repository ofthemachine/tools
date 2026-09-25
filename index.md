---
type: Catalog
title: tools ofthemachine
version: 0.1.0
description: Level-0 tools -- single-file fraglets that run in pinned containers via fragletc -- organised into packs, one directory each, published as one Agent Skill per pack.
tags:
  computation: A run is a pure function of its parameters -- no network, no clock -- so results are reproducible and memoizable.
  documents: Consumes or produces a document file -- PDF, Markdown, LaTeX, HTML, Office.
  engineering: Serves software work -- source code, structured data, token budgets, and the building of this catalog.
  internet: Reaches out to the public internet -- URLs, search, the host's own address.
  media: Consumes or produces images, diagrams, or memes.
  world: The answer depends on the state of the world at run time -- weather, news, the sky, public trivia feeds.
---

# tools ofthemachine

A **tool** is one file, in any language that has a fraglet-enabled container -- the 90-odd `100hellos/<lang>` images or the purpose-built `ofthemachine/<image>` ones (python3, headless-browser, latex, meme, home-automation, 3d-printing, ...): a shebang that pins that image, `#:` header lines that declare what it does (`d=`), when to reach for it (`when=`), its parameters, outputs, network reach and stdin stance, and a body. `fragletc` runs it, lints it, prints its help, and writes a receipt for every run. Nothing about a tool lives outside its file.

A **pack** is a root directory holding tools that share a subject. Its `index.md` gives the pack a title, a description, and tags. The pack is the unit of sharing: the build turns each pack into one Agent Skill (`SKILL.md` beside the tools), one Claude Code plugin, one entry in `llms.txt`.

## Taxonomy

Two axes. A path segment is identity; a tag is grouping.

- **Pack** (path): a subject noun -- what the tools act on or produce (`web`, `doc`, `image`, `weather`). Kebab-case, at most 20 characters. Never a verb, a runtime, or a container name. A pack that needs its own image gets one of the same name in `ofthemachine/containers`.
- **Stem** (path): what the tool gives you, so that `<pack>/<stem>` reads as the phrase someone would ask for.
  - A lookup names its result: `weather/forecast`, `astro/moon-phase`, `net/public-ip`.
  - An action is an imperative verb or verb-object, dropping the object when it is the pack: `image/transform`, `receipt/attest`, `github/read-issue-form`.
  - A conversion is `<from>-to-<to>`: `doc/markdown-to-pdf`, `web/page-to-pdf`.
  - A provider or program appears only when the tool is its interface, and then its siblings share the shape: `llm/cohere`, `data/jq`, `data/sql`, `diagram/graphviz`.
  - Never repeat the pack, and never name a consumer, a version, or a term without a common meaning. A synonym goes in `when=`, the catalog's relative index, never into a second tool.
- **Tags** (`tags:` in the pack's `index.md`): drawn from the vocabulary in this file's frontmatter, nowhere else. Each tag is a criterion, not a list of members; a pack carries every tag whose criterion its tools meet, so most packs have one and some have two. The build refuses a tag that is not listed here.
- **Title** (`title:` in the pack's `index.md`): the pack name as it is conventionally written, never pluralised -- `doc` is `Doc`, `github` is `GitHub`, `llm` is `LLM` -- so every listing spells a pack one way.

## Growth rules

1. A new tool is one file in an existing pack. A new pack is a directory, an `index.md`, and its first tool. Nothing else changes. A tool that knows nothing about the project that needed it belongs here from its first use -- an agent that cannot find it will spend tokens writing a near-copy -- while logic specific to one project (its prompts, its rendering) stays in that project's own `fraglets/`.
2. A pack may hold a single tool when its description names a subject a second tool could plausibly join.
3. Split a pack when its generated `SKILL.md` passes five hundred lines (the validator's limit; about twenty tools). Split by subject, never by verb: `web` becomes `web` and `browser`, not `web-fetch` and `web-render`.
4. A tool's stem is unique within its pack. The extension is the language and carries no identity.
5. Until the catalog has outside users, packs and stems are renamed freely whenever a better name is found, in one pass that updates every consumer. A rename changes a skill name, a URL, and the path held beside a `procedure_hash`; the protections for that come back with the first outside user.
6. When this vocabulary passes about thirty tags, adopt facets (`works-with::pdf`, `reach::lan`). One file changes; no path moves. Not before.
7. A tool that needs a specific machine (LAN devices, hardware) declares `#: network=required` and nothing more here; routing it to the machine that can run it is a scheduler's concern, not the catalog's.
