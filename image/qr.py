#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:1a6a8e9cd91c93359794245e2a36b883ee54dfef06356ff8be1d4d863ee3823a
#: d=Make a QR code (PNG or SVG) for a link or any text, computed locally with segno and no network: what it encodes never leaves the container. Text that is a secret (an invite link, a Wi-Fi password) goes on stdin, not in text=: params are written into every receipt in plain text, stdin only as a hash. Prints the code's version and size, and with show=true the code itself, drawn in the terminal.
#: when=Use when the user wants a QR code, a scannable link, or a printable code for a URL, an invite, Wi-Fi details or any short text.
#: network=none
#: stdin=buffer
#: param=text:d=What the code encodes (or pipe it on stdin, which a secret must use)
#: param=format:default=png:kind=enum(png|svg):d=png (raster) or svg (vector)
#: param=scale:default=8:kind=range(1..40):d=Pixels per module (the code's smallest square)
#: param=border:default=4:kind=range(0..10):d=Quiet zone around the code, in modules (scanners want 4)
#: param=error:default=M:kind=enum(L|M|Q|H):d=Error correction: L 7%, M 15%, Q 25%, H 30% of the code may be lost and still scan
#: param=show:default=false:kind=bool:d=Also draw the code on stdout with text blocks, to scan from a terminal
#: output=qr.png:optional
#: output=qr.svg:optional
import os
import sys

import segno

text = os.environ.get("TEXT", "")
if not text and not sys.stdin.isatty():
    text = sys.stdin.read().rstrip("\n")
if not text:
    print("Error: nothing to encode: give text=, or pipe it on stdin (a secret must use stdin)", file=sys.stderr)
    sys.exit(2)

fmt = os.environ["FORMAT"].strip().lower()
scale = int(os.environ["SCALE"])
border = int(os.environ["BORDER"])
qr = segno.make(text, error=os.environ["ERROR"].strip().upper(), micro=False)

out = f"/output/qr.{fmt}"
qr.save(out, scale=scale, border=border)
width, height = qr.symbol_size(scale=scale, border=border)
print(f"QR version {qr.version}, error {qr.error.upper()}, {width}x{height} px -> qr.{fmt}")

if os.environ["SHOW"].strip().lower() in ("1", "true", "yes"):
    qr.terminal(border=border, compact=True)
