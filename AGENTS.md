# CLAUDE.md

This repository is a catalog of **level-0 tools**: single-file fraglets, one directory (pack) per subject, compiled into one Agent Skill per pack. Nothing about a tool lives outside its file.

- `index.md` — the taxonomy: tag vocabulary and growth rules. Read it before naming a pack.
- `CONTRIBUTING.md` — how to write a tool (clone a sibling, header grammar, verification protocol).
- `make build` — lint every pack, compile `catalog/` (a fraglet in `meta/`), validate it (a fraglet in `meta/`). This is the whole review.

Composite skills, behavioral directives, and anything authored in prose belong in `ofthemachine/skills`, not here. Never add host-side scripts: build tooling is a fraglet in `meta/`, or a `fragletc` subcommand in `ofthemachine/fraglet` when it concerns the header grammar.
