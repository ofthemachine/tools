#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Slice, transform, filter, and extract JSON data using jq query expressions on JSON text or JSON files.
#: when=Use when the user wants to filter, reshape, or pull fields out of JSON, or an API payload needs trimming before it enters context.
#: network=none
#: stdin=buffer
#: param=filter:required:d=jq filter expression, e.g. .items[].name
#: param=json_source:file:d=Host JSON file mounted at /input/json_source
#: param=json_text:d=Inline JSON text (or pipe stdin)
import os
import subprocess
import sys

filter_expr = os.environ.get("FILTER", "")
json_source = os.environ.get("JSON_SOURCE", "")
json_text = os.environ.get("JSON_TEXT", "")

cmd = ["jq", "-r", filter_expr]

if json_source and os.path.exists(json_source):
    cmd.append(json_source)
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if not json_text and not sys.stdin.isatty():
    json_text = sys.stdin.read()

if not json_text:
    print("Error: No JSON provided via json_source, json_text, or stdin", file=sys.stderr)
    sys.exit(1)

res = subprocess.run(cmd, input=json_text, text=True)
sys.exit(res.returncode)
