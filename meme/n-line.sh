#!/usr/bin/env -S fragletc --image=ofthemachine/meme@sha256:e8781eb2f6282153701c4343b1109d05fef3eef28782035689719113bebdd872
#: d=Render a caption onto a meme-cli template. lines is a single "|"-delimited string, one caption per box in order, whatever the box count -- a 1-box template is just "one caption", a 2-box is "top|bottom", an 8-box is "a|b|c|d|e|f|g|h". Run explore.sh show <id> first to check the real box count/order.
#: when=Use when the user wants a meme rendered from a known template with specific captions.
#: network=none
#: stdin=none
#: param=template:required:d=meme-cli template id (find with explore.sh search/show)
#: param=lines:required:d=Captions joined by |, one per box in template order
#: output=meme.png

meme-cli render "$TEMPLATE" --lines "$LINES" -o /output/meme.png
