#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Run SQL queries on CSV, TSV, or tabular data, outputting results as Markdown, JSON, or CSV.
#: when=Use when the user wants to query, filter, aggregate, or slice tabular CSV or TSV data with SQL, or large tabular files must be summarized before entering context.
#: network=none
#: stdin=buffer
#: param=query:required:d=SQL query to run against the table named 'data' (e.g. 'SELECT status, count(*) FROM data GROUP BY status')
#: param=table_source:file:d=Host CSV/TSV file mounted at /input/table_source
#: param=table_text:d=Inline CSV/TSV text (or pipe stdin)
#: param=delimiter:default=auto:d=Column delimiter: auto, comma, tab, pipe, semicolon
#: param=format:default=markdown:d=Output format: markdown, json, csv
import csv
import io
import json
import os
import sqlite3
import sys

from tabulate import tabulate

query = os.environ.get("QUERY", "")
source_path = os.environ.get("TABLE_SOURCE", "")
inline_text = os.environ.get("TABLE_TEXT", "")
delim_spec = os.environ["DELIMITER"].strip().lower()
fmt = os.environ["FORMAT"].strip().lower()

DELIMS = {
    "auto": None,
    "comma": ",",
    ",": ",",
    "tab": "\t",
    "\t": "\t",
    "pipe": "|",
    "|": "|",
    "semicolon": ";",
    ";": ";",
}

if delim_spec not in DELIMS:
    print(f"Error: unknown delimiter '{delim_spec}' (expected auto, comma, tab, pipe, semicolon)", file=sys.stderr)
    sys.exit(1)

if fmt not in ("markdown", "json", "csv"):
    print(f"Error: unknown format '{fmt}' (expected markdown, json, csv)", file=sys.stderr)
    sys.exit(1)

# Resolve content stream
handle = None
if source_path and os.path.exists(source_path):
    handle = open(source_path, "r", encoding="utf-8", errors="replace")
elif inline_text:
    handle = io.StringIO(inline_text)
elif not sys.stdin.isatty():
    piped = sys.stdin.read()
    if piped:
        handle = io.StringIO(piped)

if handle is None:
    print("Error: No data provided via table_source, table_text, or stdin", file=sys.stderr)
    sys.exit(1)

# Determine delimiter
chosen_delim = DELIMS[delim_spec]
if chosen_delim is None:
    sample = handle.read(8192)
    handle.seek(0)
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        chosen_delim = sniffed.delimiter
    except Exception:
        chosen_delim = ","

reader = csv.reader(handle, delimiter=chosen_delim)
try:
    raw_headers = next(reader)
except StopIteration:
    print("Error: table is completely empty", file=sys.stderr)
    sys.exit(1)

# Normalize column names: ensure valid, unique names
headers = []
seen = set()
for i, h in enumerate(raw_headers, start=1):
    cleaned = h.strip() or f"col_{i}"
    base = cleaned
    count = 1
    while cleaned.lower() in seen:
        count += 1
        cleaned = f"{base}_{count}"
    seen.add(cleaned.lower())
    headers.append(cleaned)


def coerce(val: str):
    s = val.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


conn = sqlite3.connect(":memory:")
col_defs = ", ".join(f'"{h}"' for h in headers)
placeholders = ", ".join("?" for _ in headers)
conn.execute(f"CREATE TABLE data ({col_defs})")

batch = []
for row in reader:
    # Pad or trim row to match headers count
    if len(row) < len(headers):
        row = row + [""] * (len(headers) - len(row))
    elif len(row) > len(headers):
        row = row[:len(headers)]
    batch.append([coerce(c) for c in row])
    if len(batch) >= 10000:
        conn.executemany(f"INSERT INTO data VALUES ({placeholders})", batch)
        batch = []

if batch:
    conn.executemany(f"INSERT INTO data VALUES ({placeholders})", batch)

try:
    cursor = conn.execute(query)
    desc = cursor.description
    if desc is None:
        # e.g. DDL or non-selecting query
        conn.commit()
        print(f"Query executed successfully ({cursor.rowcount} rows affected).")
        sys.exit(0)
    out_cols = [d[0] for d in desc]
    rows = cursor.fetchall()
except sqlite3.Error as e:
    print(f"SQLite error: {e}", file=sys.stderr)
    sys.exit(1)

if fmt == "markdown":
    if not rows:
        print("(no rows returned)")
    else:
        print(tabulate(rows, headers=out_cols, tablefmt="github"))
elif fmt == "json":
    records = [dict(zip(out_cols, r)) for r in rows]
    print(json.dumps(records, indent=2))
elif fmt == "csv":
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(out_cols)
    writer.writerows(rows)
    sys.stdout.write(out.getvalue())
