#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:8ac6f2f481f40e32a0b2f8dd7a834fd03197b1556bd8f55b1f167cd71d4877b0
#: d=Render Markdown to one PDF with headless Chromium: inline text, a single .md (or .html) file, or a tar/tar.gz/zip bundle of pages plus the images and fonts they reference by relative path. Several pages become one document with page breaks (ordered by manifest.txt/order.txt when present, else by path) and a table of contents. style=reader applies clean reader typography; style=none renders the page exactly as authored, adding only the page box -- for pages that bring their own <style>, like newspapers, posters, and one-sheets.
#: when=Use when the user wants a PDF of some Markdown -- one note, a folder of documents compiled into a digest, or a designed page with its own assets and styling.
#: network=none
#: stdin=buffer
#: param=source:file:d=A .md or .html file, or a tar/tar.gz/zip bundle of pages and their assets
#: param=text:d=Inline Markdown (or pipe stdin), when there is no source file
#: param=page:d=Render only this entry of a bundle (e.g. index.html); omitted, every .md in the bundle
#: param=style:default=reader:d=reader (house typography) or none (the page exactly as authored, plus the page box)
#: param=toc:default=auto:d=Table of contents: auto (when there is more than one page), true, or false
#: param=title:d=Document title, shown as a heading above the contents (reader style only)
#: param=size:default=A4:d=Paper size (A4, Letter, ...)
#: param=margin:d=Page margin on all sides (default 18mm for reader, 12mm for none)
#: output=document.pdf
import html
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile

import markdown
from playwright.sync_api import sync_playwright

READER_CSS = """
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         line-height: 1.6; color: #1e293b; max-width: 820px; margin: 0 auto; font-size: 11pt; }
  .cover { margin-bottom: 2.5em; padding-bottom: 1.2em; border-bottom: 3px solid #0f172a; }
  .cover h1 { font-size: 26pt; font-weight: 800; margin: 0; border: 0; }
  .toc { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.2em 1.5em; margin-bottom: 2.5em; }
  .toc h2 { font-size: 12pt; text-transform: uppercase; letter-spacing: .04em; margin: 0 0 .8em; border: 0; }
  .toc ul { list-style: none; padding: 0; margin: 0; } .toc li { padding: .4em 0; border-bottom: 1px dashed #e2e8f0; }
  .toc a { color: #0f172a; text-decoration: none; font-weight: 500; }
  .section + .section { page-break-before: always; }
  h1, h2, h3, h4 { color: #0f172a; font-weight: 700; margin: 1.4em 0 .5em; line-height: 1.25; }
  h1 { font-size: 20pt; border-bottom: 2px solid #e2e8f0; padding-bottom: .3em; }
  h2 { font-size: 15pt; border-bottom: 1px solid #edf2f7; padding-bottom: .2em; } h3 { font-size: 13pt; }
  p { margin-bottom: 1em; text-align: justify; } a { color: #2563eb; text-decoration: none; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 9.5pt;
         background: #f1f5f9; padding: .15em .35em; border-radius: 4px; }
  pre { background: #0f172a; color: #f8fafc; padding: 12px; border-radius: 6px; font-size: 9pt; line-height: 1.45; }
  pre code { background: transparent; color: inherit; padding: 0; }
  blockquote { border-left: 4px solid #3b82f6; margin: 1.2em 0; padding-left: 1em; color: #475569; font-style: italic; }
  table { width: 100%; border-collapse: collapse; margin: 1.5em 0; }
  th, td { border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; font-size: 10pt; } th { background: #f8fafc; }
  img { max-width: 100%; height: auto; display: block; margin: 1.5em auto; }
"""


def fail(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def safe_extract(archive, dest):
    root = os.path.abspath(dest)
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tar:
            for m in tar.getmembers():
                if os.path.commonpath([root, os.path.abspath(os.path.join(dest, m.name))]) == root:
                    tar.extract(m, dest)
    else:
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if os.path.commonpath([root, os.path.abspath(os.path.join(dest, name))]) == root:
                    zf.extract(name, dest)


def title_of(text, path):
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ").title()


def strip_front_matter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if line.startswith("title:"):
                    return parts[2], line.split(":", 1)[1].strip().strip("\"'")
            return parts[2], None
    return text, None


style = os.environ["STYLE"].strip().lower()
if style not in ("reader", "none"):
    fail("style must be reader or none")
work = tempfile.mkdtemp(prefix="md2pdf_")
try:
    # Collect the pages: (path on disk, source text), rendered in order from one directory.
    source = os.environ.get("SOURCE", "")
    pages, base = [], work
    if source and (tarfile.is_tarfile(source) or zipfile.is_zipfile(source)):
        safe_extract(source, work)
        files = sorted(os.path.relpath(os.path.join(r, f), work) for r, _, fs in os.walk(work)
                       for f in fs if not f.startswith(("._", ".")))
        want = os.environ.get("PAGE", "").strip().lstrip("./")
        if want:
            match = [f for f in files if f == want or f.endswith("/" + want)]
            if len(match) != 1:
                fail(f"page {want!r} not found (once) in the bundle; it holds: {', '.join(files) or 'nothing'}")
            chosen = match
        else:
            order = next((f for f in files if os.path.basename(f) in ("manifest.txt", "order.txt", "index.txt")), None)
            listed = []
            if order:
                odir = os.path.dirname(order)
                for line in open(os.path.join(work, order), encoding="utf-8"):
                    line = line.split("#", 1)[0].strip()
                    if line and os.path.join(odir, line) in files:
                        listed.append(os.path.join(odir, line))
            chosen = listed or [f for f in files if f.endswith((".md", ".markdown"))]
        if not chosen:
            fail("no .md pages in the bundle (name one with page=)")
        pages = [(os.path.join(work, f), open(os.path.join(work, f), encoding="utf-8", errors="replace").read()) for f in chosen]
        base = os.path.dirname(pages[0][0]) if len(pages) == 1 else work
    elif source:
        text = open(source, encoding="utf-8", errors="replace").read()
        pages = [("document.md" if not text.lstrip().startswith("<") else "document.html", text)]
    else:
        text = os.environ.get("TEXT", "") or (sys.stdin.read() if not sys.stdin.isatty() else "")
        if not text.strip():
            fail("nothing to render: pass source=<file or bundle>, text=<markdown>, or pipe stdin")
        pages = [("document.md", text)]

    sections, toc = [], []
    for i, (path, text) in enumerate(pages, 1):
        if path.lower().endswith((".html", ".htm")):
            body, name = text, os.path.basename(path)
        else:
            text, fm_title = strip_front_matter(text)
            body = markdown.markdown(text, extensions=["extra", "tables", "toc"] + (["codehilite"] if style == "reader" else []))
            name = fm_title or title_of(text, path)
        toc.append((f"s{i}", name))
        sections.append(f'<div class="section" id="s{i}">{body}</div>' if style == "reader" else body)

    toc_mode = os.environ["TOC"].strip().lower()
    show_toc = style == "reader" and (toc_mode == "true" or (toc_mode == "auto" and len(pages) > 1))
    title = os.environ.get("TITLE", "").strip()
    margin = os.environ.get("MARGIN", "").strip() or ("18mm" if style == "reader" else "12mm")
    size = os.environ["SIZE"].strip()
    head = (f'<div class="cover"><h1>{html.escape(title)}</h1></div>' if title and style == "reader" else "")
    if show_toc:
        head += '<div class="toc"><h2>Contents</h2><ul>' + "".join(
            f'<li><a href="#{sid}">{html.escape(n)}</a></li>' for sid, n in toc) + "</ul></div>"
    css = f"@page {{ size: {size}; margin: {margin}; }}\n" + (READER_CSS if style == "reader" else "body { margin: 0; } img { max-width: 100%; }")
    document = f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><style>{css}</style></head><body>{head}{"".join(sections)}</body></html>'

    # Written beside the pages, so relative src/href in a bundle resolve as authored.
    render = os.path.join(base, "_render.html")
    with open(render, "w", encoding="utf-8") as f:
        f.write(document)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        tab = browser.new_page()
        tab.goto(f"file://{render}", wait_until="load")
        tab.pdf(path="/output/document.pdf", format=size, print_background=True, prefer_css_page_size=True,
                margin={"top": margin, "bottom": margin, "left": margin, "right": margin})
        browser.close()
    print(f"{len(pages)} page(s), style={style}, toc={'yes' if show_toc else 'no'} -> document.pdf "
          f"({os.path.getsize('/output/document.pdf'):,} bytes)")
finally:
    shutil.rmtree(work, ignore_errors=True)
