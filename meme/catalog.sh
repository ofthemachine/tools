#!/usr/bin/env -S fragletc --image ofthemachine/meme@sha256:8a3ac29b110b9471e7688bf8d7bdc12fe83fd49da63a084a3db1a41549b6c57f
#: d=Dump the whole meme catalog in one run: meme-cli list --json. Each template's alias is its id, its field count is the length of text_boxes, and its description is name. The image has no shell, so this is its own fraglet rather than a flag on templates.sh.
#: when=Use when a caller needs every template at once — alias, field count, description — to choose one.
#: network=none
#: stdin=none
meme-cli list --json
