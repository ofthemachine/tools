#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Calculate BPE token counts and token statistics for text or files using OpenAI tiktoken tokenizers (cl100k_base or o200k_base).
#: when=Use when the user asks how many tokens some text or file is, or a prompt must be checked against a token budget.
#: network=required
#: stdin=buffer
#: param=text:d=Inline text to tokenize (or pipe stdin)
#: param=encoding:default=cl100k_base:description=tiktoken encoding or model name
# network=required only because tiktoken downloads its BPE table on first use;
# the pinned python3 image does not bake a TIKTOKEN_CACHE_DIR yet. Pure computation otherwise.
import os
import sys
import tiktoken

text = os.environ.get("TEXT", "")
encoding_name = os.environ["ENCODING"]

if not text:
    if not sys.stdin.isatty():
        text = sys.stdin.read()

if not text:
    print("Error: No input text provided via TEXT parameter or stdin", file=sys.stderr)
    sys.exit(1)

try:
    enc = tiktoken.get_encoding(encoding_name)
except Exception:
    try:
        enc = tiktoken.encoding_for_model(encoding_name)
    except Exception as e:
        print(f"Error: Unknown encoding or model '{encoding_name}': {e}", file=sys.stderr)
        sys.exit(1)

tokens = enc.encode(text)
token_count = len(tokens)
char_count = len(text)
word_count = len(text.split())
lines_count = len(text.splitlines())
ratio = char_count / token_count if token_count > 0 else 0

print(f"Tokens:     {token_count}")
print(f"Characters: {char_count}")
print(f"Words:      {word_count}")
print(f"Lines:      {lines_count}")
print(f"Chars/Tok:  {ratio:.2f}")
print(f"Encoding:   {enc.name}")
