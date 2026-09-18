#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Split text into token-budgeted chunks using OpenAI tiktoken encodings, preferring paragraph boundaries and hard-splitting only paragraphs that exceed the budget on their own. Each chunk is introduced by a "[chunk i/n tokens=k]" marker line, and overlap carries that many tokens of tail context into the next chunk so meaning is not severed mid-thought. Use when text is too large for a single context window, or to prepare passages for embedding. Companion to token-counter, which measures the problem this solves.
#: when=Use when text is too large for one prompt and must be split into token-budgeted pieces that respect paragraph boundaries.
#: network=required
#: stdin=buffer
#: param=text:d=Inline text to chunk (or pipe stdin)
#: param=text_source:file:d=Host file mounted at /input/text_source
#: param=max_tokens:default=1000:d=Token budget per chunk
#: param=overlap:default=100:d=Tail tokens carried into the next chunk
#: param=encoding:default=cl100k_base:description=tiktoken encoding or model name
# network=required only because tiktoken downloads its BPE table on first use;
# the pinned python3 image does not bake a TIKTOKEN_CACHE_DIR yet. Pure computation otherwise.
import os
import sys

import tiktoken

text = os.environ.get("TEXT", "")
text_source = os.environ.get("TEXT_SOURCE", "")
encoding_name = os.environ["ENCODING"]

if text_source and os.path.exists(text_source):
    with open(text_source, "r", errors="ignore") as f:
        text = f.read()

if not text and not sys.stdin.isatty():
    text = sys.stdin.read()

if not text.strip():
    print("Error: No input text provided via text, text_source, or stdin", file=sys.stderr)
    sys.exit(1)


def bounded_int(name: str, minimum: int) -> int:
    raw = os.environ[name].strip()
    try:
        value = int(raw)
    except ValueError:
        print(f"Error: {name.lower()} must be an integer, got '{raw}'", file=sys.stderr)
        sys.exit(1)
    if value < minimum:
        print(f"Error: {name.lower()} must be at least {minimum}, got {value}", file=sys.stderr)
        sys.exit(1)
    return value


max_tokens = bounded_int("MAX_TOKENS", 1)
overlap = bounded_int("OVERLAP", 0)

if overlap >= max_tokens:
    print(f"Error: overlap ({overlap}) must be smaller than max_tokens ({max_tokens})", file=sys.stderr)
    sys.exit(1)

try:
    enc = tiktoken.get_encoding(encoding_name)
except Exception:
    try:
        enc = tiktoken.encoding_for_model(encoding_name)
    except Exception as e:
        print(f"Error: Unknown encoding or model '{encoding_name}': {e}", file=sys.stderr)
        sys.exit(1)

# Paragraphs are the natural seam; anything longer than the budget on its own
# gets sliced by token index, which is the only boundary guaranteed to fit.
units = []
for para in text.split("\n\n"):
    if not para.strip():
        continue
    tokens = enc.encode(para)
    if len(tokens) <= max_tokens:
        units.append(tokens)
        continue
    for start in range(0, len(tokens), max_tokens):
        units.append(tokens[start:start + max_tokens])

separator = enc.encode("\n\n")
chunks = []
current: list = []
for unit in units:
    candidate = current + (separator if current else []) + unit
    if current and len(candidate) > max_tokens:
        chunks.append(current)
        carried = current[-overlap:] + separator if overlap else []
        # Drop the carry rather than blow the budget it exists to respect.
        current = carried + unit if len(carried) + len(unit) <= max_tokens else unit
    else:
        current = candidate
if current:
    chunks.append(current)

for i, chunk in enumerate(chunks, start=1):
    print(f"[chunk {i}/{len(chunks)} tokens={len(chunk)}]")
    print(enc.decode(chunk))
    print()
