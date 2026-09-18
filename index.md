---
type: Catalog
title: ofthemachine tools
version: 0.1.0
description: Level-0 tools -- single-file fraglets that run in pinned containers via fragletc -- organised into packs, one directory each, published as one Agent Skill per pack.
tags:
  computation: Pure functions over their inputs -- math, text, encodings.
  documents: Producing and reading documents -- PDF, Markdown, LaTeX, Office.
  engineering: Software work -- code, data, tokens, and this catalog's own build.
  internet: The network as seen from here -- URLs, search, the host's address.
  media: Images, diagrams, and memes.
  world: Facts about the world right now -- weather, news, sky, trivia.
---

# ofthemachine tools

A **tool** is one file: a shebang that pins a container image, `#:` header lines that declare what it does (`d=`), when to reach for it (`when=`), its parameters, outputs, network reach and stdin stance, and a body. `fragletc` runs it, lints it, prints its help, and writes a receipt for every run. Nothing about a tool lives outside its file.

A **pack** is a root directory holding tools that share a subject. Its `index.md` gives the pack a title, a description, and tags. The pack is the unit of sharing: the build turns each pack into one Agent Skill (`SKILL.md` beside the tools), one Claude Code plugin, one entry in `llms.txt`.

## Taxonomy

Two axes. A path segment is identity; a tag is grouping.

- **Pack** (path): a subject noun -- what the tools act on or produce (`web`, `doc`, `image`, `weather`). Kebab-case, at most 20 characters. Never a verb, a runtime, or a container name. A pack that needs its own image gets one of the same name in `ofthemachine/containers`.
- **Tags** (`tags:` in the pack's `index.md`): drawn from the vocabulary in this file's frontmatter, nowhere else. The build refuses a tag that is not listed here.

## Growth rules

1. A new tool is one file in an existing pack. A new pack is a directory, an `index.md`, and its first tool. Nothing else changes.
2. A pack may hold a single tool when its description names a subject a second tool could plausibly join.
3. Split a pack when its generated `SKILL.md` passes about twenty tools or two hundred lines. Split by subject, never by verb: `web` becomes `web` and `browser`, not `web-fetch` and `web-render`.
4. A tool's stem is unique within its pack. The extension is the language and carries no identity.
5. Renaming a pack or a stem is a breaking change: it changes a skill name, a URL, and the path consumers hold beside a `procedure_hash`. Pack renames are recorded in `marketplace.json` under `renames`.
6. When this vocabulary passes about thirty tags, adopt facets (`works-with::pdf`, `reach::lan`). One file changes; no path moves. Not before.
7. A tool that needs a specific machine (LAN devices, hardware) declares `#: network=required` and nothing more here; routing it to the machine that can run it is a scheduler's concern, not the catalog's.
