#!/usr/bin/env -S fragletc --image=ofthemachine/meme@sha256:e8781eb2f6282153701c4343b1109d05fef3eef28782035689719113bebdd872 --output-dir=.
#: d=Explore and discover meme templates (search, show details/box count, list popular templates, or output LLM guidelines). Generic passthrough tool for meme-cli.
#: when=Use when the user wants to find a meme template, check a template's box count and order, list popular templates, or read meme-cli's guidance for LLMs.
#: network=none
#: stdin=none
# Generic passthrough (no declared params/output -- see README.md).
# Use for discovery (search/show/list/llms) and for the long tail of
# 4+ box templates the shaped scripts don't cover.
meme-cli "$@"
