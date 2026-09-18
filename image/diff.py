#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Compare two images pixel by pixel and report a machine-readable verdict (VERDICT: IDENTICAL or VERDICT: DIFFERENT) with the changed-pixel percentage, maximum channel delta, and bounding box of the change, alongside a PNG that tints every changed region red over the after image. Set tolerance to ignore per-channel noise below a 0-255 threshold, such as antialiasing jitter.
#: when=Use when the user wants to know whether two images differ, how much, and where -- visual regression checks, before/after comparisons.
#: network=none
#: stdin=none
#: param=before:required:file:d=Baseline image
#: param=after:required:file:d=Comparison image
#: param=tolerance:default=0:description=Ignore per-channel deltas below this 0-255 threshold
#: output=diff.png
import os
import sys

from PIL import Image, ImageChops, ImageDraw

before_path = os.environ.get("BEFORE", "")
after_path = os.environ.get("AFTER", "")
tolerance = int(os.environ["TOLERANCE"])

for label, path in (("before", before_path), ("after", after_path)):
    if not path or not os.path.exists(path):
        print(f"Error: {label} file '{path}' does not exist", file=sys.stderr)
        sys.exit(1)

before = Image.open(before_path)
after = Image.open(after_path)
before_size, after_size = before.size, after.size
size_mismatch = before_size != after_size

# Compare on a canvas big enough for both, so a resized page still diffs
# instead of erroring out; the padding reads as changed, which is correct.
canvas = (max(before_size[0], after_size[0]), max(before_size[1], after_size[1]))


def on_canvas(img):
    rgb = Image.new("RGB", canvas, (0, 0, 0))
    rgb.paste(img.convert("RGB"), (0, 0))
    return rgb


before_rgb = on_canvas(before)
after_rgb = on_canvas(after)

delta = ImageChops.difference(before_rgb, after_rgb)
max_delta = max(band.getextrema()[1] for band in delta.split())

# Flatten the per-channel delta to a single mask of "this pixel changed".
flat = delta.convert("L").point(lambda v: 255 if v > tolerance else 0)
changed = sum(count for value, count in enumerate(flat.histogram()) if value and count)
total = canvas[0] * canvas[1]
bbox = flat.getbbox()

highlight = after_rgb.copy()
if bbox:
    tint = Image.new("RGB", canvas, (255, 0, 0))
    highlight.paste(tint, (0, 0), flat)
    ImageDraw.Draw(highlight).rectangle(bbox, outline=(255, 0, 0), width=3)
highlight.save("/output/diff.png", format="PNG")

verdict = "DIFFERENT" if (changed or size_mismatch) else "IDENTICAL"
print(f"VERDICT: {verdict}")
print(f"before: {before_size[0]}x{before_size[1]} {before.format or '?'}")
print(f"after: {after_size[0]}x{after_size[1]} {after.format or '?'}")
print(f"dimensions: {'MISMATCH' if size_mismatch else 'MATCH'}")
print(f"changed pixels: {changed:,} / {total:,} ({100 * changed / total:.2f}%)")
print(f"max channel delta: {max_delta}")
print(f"bounding box: {bbox if bbox else 'none'}")
