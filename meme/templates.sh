#!/usr/bin/env -S fragletc --image=ofthemachine/meme@sha256:8a3ac29b110b9471e7688bf8d7bdc12fe83fd49da63a084a3db1a41549b6c57f --output-dir=.
#: d=Browse meme-cli's template library: templates.sh search <term>, templates.sh show <template> (boxes and their order), templates.sh list (popular templates), or templates.sh llms (meme-cli's guidance for LLMs). Arguments pass straight through to meme-cli; there are no -p parameters.
#: when=Use when the user wants to find a meme template, check a template's box count and order, list popular templates, or read meme-cli's guidance for LLMs.
#: network=none
#: stdin=none
# Generic passthrough (no declared params/output -- see README.md).
# Use for discovery (search/show/list/llms) and for the long tail of
# 4+ box templates the shaped scripts don't cover.
meme-cli "$@"
