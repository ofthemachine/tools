#!/usr/bin/env -S fragletc --image ofthemachine/meme@sha256:8a3ac29b110b9471e7688bf8d7bdc12fe83fd49da63a084a3db1a41549b6c57f
#: d=Every meme template, one per line: its id, how many captions it takes ("2 boxes") and its name, in columns at least two spaces apart (meme-cli list). For keywords and box geometry, meme/catalog's JSON.
#: when=Use when a caller needs the template ids to choose from, as plain lines.
#: network=none
#: stdin=none
meme-cli list
