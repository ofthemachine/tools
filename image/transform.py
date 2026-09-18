#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Resize, crop, convert, and compress images (PNG, JPEG, WebP, GIF, TIFF, BMP), reporting the byte savings on stdout. Set max_dimension to fit the longest edge inside a box while preserving aspect ratio, or give width and/or height directly; crop takes "x,y,w,h" in pixels and is applied before any resize. Shrinks oversized screenshots before they consume an agent's context or get embedded in a PDF.
#: when=Use when an image must be resized, cropped, converted to another format, or compressed to a smaller file size.
#: network=none
#: stdin=none
#: param=image:required:file:d=Source image mounted at /input/image
#: param=max_dimension:d=Fit longest edge inside this many pixels
#: param=width:d=Target width in pixels
#: param=height:d=Target height in pixels
#: param=crop:d=Crop box as x,y,w,h in pixels (before resize)
#: param=format:d=Output format (PNG, JPEG, WEBP, …); default keeps source
#: param=quality:default=85:d=JPEG/WebP quality 1-100
#: param=grayscale:default=false:d=Convert to grayscale when true
#: output=image
import os
import sys

from PIL import Image

src = os.environ.get("IMAGE", "")
crop_spec = os.environ.get("CROP", "").strip()
out_format = os.environ.get("FORMAT", "").strip().upper()
quality = int(os.environ["QUALITY"])
grayscale = os.environ["GRAYSCALE"].strip().lower() in ("1", "true", "yes")

if not src or not os.path.exists(src):
    print(f"Error: image file '{src}' does not exist", file=sys.stderr)
    sys.exit(1)


def positive_int(name: str):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        print(f"Error: {name.lower()} must be an integer, got '{raw}'", file=sys.stderr)
        sys.exit(1)
    if value <= 0:
        print(f"Error: {name.lower()} must be positive, got {value}", file=sys.stderr)
        sys.exit(1)
    return value


max_dimension = positive_int("MAX_DIMENSION")
width = positive_int("WIDTH")
height = positive_int("HEIGHT")

img = Image.open(src)
src_format = img.format or "PNG"
src_size = img.size
src_bytes = os.path.getsize(src)

if crop_spec:
    try:
        x, y, w, h = (int(v.strip()) for v in crop_spec.split(","))
    except ValueError:
        print(f"Error: crop must be 'x,y,w,h' in pixels, got '{crop_spec}'", file=sys.stderr)
        sys.exit(1)
    img = img.crop((x, y, x + w, y + h))

if max_dimension:
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
elif width and height:
    img = img.resize((width, height), Image.LANCZOS)
elif width:
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
elif height:
    img = img.resize((round(img.width * height / img.height), height), Image.LANCZOS)

if grayscale:
    img = img.convert("L")

target_format = out_format or src_format
if target_format == "JPG":
    target_format = "JPEG"

# JPEG has no alpha channel; flatten transparency onto white rather than failing.
if target_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
    img = img.convert("RGBA")
    flattened = Image.new("RGB", img.size, (255, 255, 255))
    flattened.paste(img, mask=img.split()[-1])
    img = flattened

save_args = {}
if target_format in ("JPEG", "WEBP"):
    save_args["quality"] = quality

dest = "/output/image"
try:
    img.save(dest, format=target_format, **save_args)
except (KeyError, OSError) as e:
    print(f"Error: cannot write {target_format}: {e}", file=sys.stderr)
    sys.exit(1)

out_bytes = os.path.getsize(dest)
delta = 100 * (out_bytes / src_bytes - 1) if src_bytes else 0.0
print(f"source: {src_size[0]}x{src_size[1]} {src_format} {src_bytes:,} bytes")
print(f"output: {img.size[0]}x{img.size[1]} {target_format} {out_bytes:,} bytes")
print(f"change: {delta:+.1f}% bytes")
