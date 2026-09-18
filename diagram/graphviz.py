#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Render Graphviz DOT source into an SVG, PNG, PDF, or JSON diagram. Choose a layout engine with engine=dot for hierarchies, neato or fdp for spring layouts, circo for cyclic structures, twopi for radial trees, or sfdp for large graphs. Source comes from the dot parameter, a dot_source file, or stdin, so a model can write the graph and this tool renders it deterministically.
#: when=Use when the user has Graphviz DOT source, or wants a graph, tree, flowchart, or network drawn from a description that maps to DOT.
#: network=none
#: stdin=buffer
#: param=dot:d=Inline DOT source (or pipe stdin)
#: param=dot_source:file:d=Host DOT file mounted at /input/dot_source
#: param=engine:default=dot:description=Layout engine (dot, neato, fdp, circo, twopi, sfdp, …)
#: param=format:default=svg:description=Output format (svg, png, pdf, json, …)
#: output=diagram
import os
import subprocess
import sys

ENGINES = ("dot", "neato", "fdp", "circo", "twopi", "sfdp", "patchwork", "osage")
FORMATS = ("svg", "png", "pdf", "json", "gif", "jpg", "ps", "dot", "plain")

source = os.environ.get("DOT", "")
dot_source = os.environ.get("DOT_SOURCE", "")
engine = os.environ["ENGINE"].strip()
fmt = os.environ["FORMAT"].strip().lower()

if engine not in ENGINES:
    print(f"Error: unknown engine '{engine}' (expected one of {', '.join(ENGINES)})", file=sys.stderr)
    sys.exit(1)

if fmt not in FORMATS:
    print(f"Error: unknown format '{fmt}' (expected one of {', '.join(FORMATS)})", file=sys.stderr)
    sys.exit(1)

if dot_source and os.path.exists(dot_source):
    with open(dot_source, "r", errors="ignore") as f:
        source = f.read()

if not source and not sys.stdin.isatty():
    source = sys.stdin.read()

if not source.strip():
    print("Error: No DOT source provided via dot, dot_source, or stdin", file=sys.stderr)
    sys.exit(1)

proc = subprocess.run(
    [engine, f"-T{fmt}", "-o", "/output/diagram"],
    input=source,
    text=True,
    stderr=subprocess.PIPE,
)

if proc.returncode != 0:
    print(proc.stderr.strip() or f"{engine} failed with exit code {proc.returncode}", file=sys.stderr)
    sys.exit(proc.returncode)

if proc.stderr.strip():
    print(proc.stderr.strip(), file=sys.stderr)

print(f"rendered {fmt} via {engine}: {os.path.getsize('/output/diagram'):,} bytes")
