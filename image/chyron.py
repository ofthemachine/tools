#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Draw a TV-news lower third as a PNG: a studio backdrop, a red kicker box (BREAKING, LIVE, DEVELOPING), the headline bar, an optional ticker strip along the bottom, and the show's name as the corner bug. A still for a satirical or real broadcast; meme/caption puts text on a meme template instead.
#: when=Use when a news-style card, chyron, lower third or "breaking news" banner is wanted for a headline.
#: network=none
#: stdin=none
#: param=headline:required:d=The headline across the bar, one line (long ones are shrunk, then cut with an ellipsis)
#: param=kicker:default=BREAKING:d=The word in the red box before the headline, e.g. BREAKING, LIVE, DEVELOPING
#: param=ticker:d=Text for the ticker strip along the bottom; empty: no ticker
#: param=show:default=NEWS:d=The show's name, drawn as the corner bug
#: param=width:default=1280:kind=range(320..3840):d=Image width in pixels (height is 9/16 of it)
#: param=mood:default=on-air:kind=enum(on-air|frazzled|beaming):d=How the anchor looks: on-air (composed), frazzled (hair up, tie loose, sweating) or beaming (a grin)
#: output=chyron.png
import os
import sys

from PIL import Image, ImageDraw, ImageFont

headline = os.environ.get("HEADLINE", "").strip()
kicker = os.environ.get("KICKER", "").strip().upper()
# The container's only font has no bullets or dingbats: separators become a bar.
ticker = " ".join(os.environ.get("TICKER", "").translate({ord(c): " | " for c in "•·●▪◆★"}).split())
show = os.environ.get("SHOW", "").strip().upper()
mood = os.environ.get("MOOD", "").strip().lower()
try:
    width = int(os.environ.get("WIDTH", ""))
except ValueError:
    sys.exit("width must be a whole number of pixels")
width = max(320, min(3840, width))
if not headline:
    sys.exit("headline is empty")
headline = " ".join(headline.split())
height = width * 9 // 16
u = width / 1280  # one unit at the reference width


def font(size):
    # The container has no system fonts; Pillow's default is scalable.
    return ImageFont.load_default(size=max(8, round(size * u)))


img = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(img)

# Studio backdrop: a deep blue gradient with soft vertical light bands.
for y in range(height):
    t = y / height
    draw.line([(0, y), (width, y)], fill=(int(8 + 20 * t), int(22 + 30 * t), int(58 + 60 * (1 - t))))
for i in range(6):
    x = int(width * (0.08 + i * 0.17))
    band = Image.new("L", (int(60 * u), height), 22)
    img.paste((70, 110, 190), (x, 0), band)
# A desk across the bottom third.
desk_top = int(height * 0.62)
draw.rectangle([0, desk_top, width, height], fill=(12, 18, 34))
draw.rectangle([0, desk_top, width, desk_top + int(4 * u)], fill=(200, 160, 60))

# The anchor at the desk: shoulders, a tie, a head of hair, drawn as the
# mood says.
cx, top = int(width * 0.5), int(height * 0.22)
frazzled, beaming = mood == "frazzled", mood == "beaming"
draw.rounded_rectangle([cx - 150 * u, desk_top - 120 * u, cx + 150 * u, desk_top + 40 * u], radius=int(60 * u), fill=(34, 38, 52))
draw.polygon([(cx - 40 * u, desk_top - 120 * u), (cx, desk_top - 40 * u), (cx + 40 * u, desk_top - 120 * u)], fill=(236, 236, 240))
tie_dx = 18 * u if frazzled else 0  # a loosened tie hangs off to one side
tie_dy = 14 * u if frazzled else 0
draw.polygon([(cx - 12 * u + tie_dx, desk_top - 112 * u + tie_dy), (cx + 12 * u + tie_dx, desk_top - 112 * u + tie_dy), (cx + 16 * u + tie_dx, desk_top - 50 * u + tie_dy), (cx + tie_dx, desk_top - 34 * u + tie_dy), (cx - 16 * u + tie_dx, desk_top - 50 * u + tie_dy)], fill=(190, 30, 40))
draw.rectangle([cx - 22 * u, desk_top - 150 * u, cx + 22 * u, desk_top - 118 * u], fill=(226, 184, 150))
skin = (240, 176, 150) if frazzled else (232, 192, 158)
draw.ellipse([cx - 62 * u, top, cx + 62 * u, top + 150 * u], fill=skin)
hair = (92, 58, 30)
draw.chord([cx - 76 * u, top - 34 * u, cx + 80 * u, top + 92 * u], 180, 360, fill=hair)
if frazzled:  # the hair has given up
    for i in range(7):
        x = cx - 60 * u + i * 20 * u
        draw.polygon([(x, top + 4 * u), (x + 10 * u, top - 46 * u - (i % 3) * 8 * u), (x + 20 * u, top + 4 * u)], fill=hair)
    draw.ellipse([cx + 44 * u, top + 40 * u, cx + 54 * u, top + 56 * u], fill=(170, 210, 240))  # a bead of sweat
draw.ellipse([cx - 30 * u, top + 60 * u, cx - 14 * u, top + 72 * u], fill=(30, 30, 40))
draw.ellipse([cx + 14 * u, top + 60 * u, cx + 30 * u, top + 72 * u], fill=(30, 30, 40))
if beaming:
    draw.chord([cx - 34 * u, top + 82 * u, cx + 34 * u, top + 126 * u], 0, 180, fill=(120, 40, 40))
    draw.rectangle([cx - 26 * u, top + 104 * u, cx + 26 * u, top + 110 * u], fill=(250, 250, 250))
elif frazzled:
    draw.line([cx - 22 * u, top + 104 * u, cx - 8 * u, top + 98 * u, cx + 8 * u, top + 106 * u, cx + 22 * u, top + 100 * u], fill=(120, 50, 50), width=max(2, int(4 * u)))
else:
    draw.arc([cx - 28 * u, top + 88 * u, cx + 28 * u, top + 118 * u], 20, 160, fill=(120, 50, 50), width=max(2, int(4 * u)))
draw.rectangle([0, desk_top, width, height], fill=(12, 18, 34))
draw.rectangle([0, desk_top, width, desk_top + int(4 * u)], fill=(200, 160, 60))

# The corner bug: the show's name with a LIVE dot.
bug = font(30)
pad = int(18 * u)
draw.ellipse([pad, pad + 6 * u, pad + 18 * u, pad + 24 * u], fill=(230, 40, 40))
draw.text((pad + 28 * u, pad), show, font=bug, fill=(240, 240, 245))

# The lower third: kicker box, then the headline bar.
bar_top = int(height * 0.70)
bar_h = int(86 * u)
kick_font = font(34)
kick_w = int(draw.textlength(kicker, font=kick_font) + 40 * u) if kicker else 0
if kicker:
    draw.rectangle([0, bar_top, kick_w, bar_top + bar_h], fill=(200, 24, 30))
    draw.text((20 * u, bar_top + (bar_h - 34 * u) / 2 - 2 * u), kicker, font=kick_font, fill=(255, 255, 255))
draw.rectangle([kick_w, bar_top, width, bar_top + bar_h], fill=(245, 245, 248))

room = width - kick_w - 48 * u
size = 40
text = headline
while size > 18 and draw.textlength(text, font=font(size)) > room:
    size -= 2
head_font = font(size)
while draw.textlength(text + "…", font=head_font) > room and len(text) > 1:
    text = text[:-1]
if text != headline:
    text = text.rstrip() + "…"
draw.text((kick_w + 24 * u, bar_top + (bar_h - size * u) / 2 - 2 * u), text, font=head_font, fill=(16, 20, 32))

# The ticker strip.
if ticker:
    t_top = bar_top + bar_h + int(14 * u)
    t_h = int(44 * u)
    draw.rectangle([0, t_top, width, t_top + t_h], fill=(20, 24, 40))
    tick_font = font(24)
    line = ticker
    while draw.textlength(line, font=tick_font) > width - 40 * u and len(line) > 1:
        line = line[:-1]
    draw.text((20 * u, t_top + (t_h - 24 * u) / 2 - 2 * u), line, font=tick_font, fill=(230, 200, 90))

os.makedirs("/output", exist_ok=True)
img.save("/output/chyron.png", optimize=True)
print(f"chyron.png {width}x{height}: {kicker + ': ' if kicker else ''}{text}")
