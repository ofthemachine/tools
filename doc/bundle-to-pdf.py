#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:8ac6f2f481f40e32a0b2f8dd7a834fd03197b1556bd8f55b1f167cd71d4877b0
#: d=Render one Markdown or HTML page together with its relative assets (images, fonts) from a tar/tar.gz/zip bundle into a PDF, verbatim -- no injected title, table of contents, typography or page breaks; the page brings its own <style>. Companion to doc/markdown-to-pdf.py (single file, house style, no assets) and doc/markdowns-to-pdf.py (multi-file digest with chrome). Use for anything designed as a page: newspapers, posters, one-sheets.
#: when=Use when a page and its relative assets must be rendered to PDF exactly as authored, with no injected title, table of contents, or styling.
#: network=none
#: stdin=none
#: param=archive:required:file:d=tar/tar.gz/zip containing the page and the assets it references by relative path
#: param=page:default=index.md:d=Entry file inside the bundle (.md is converted with python-markdown extra+tables; .html is used as-is)
#: param=size:default=A4:d=Paper size passed to Chromium (A4, Letter, ...)
#: param=margin:default=12mm:d=Page margin on all sides
#: output=document.pdf
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile

import markdown
from playwright.sync_api import sync_playwright

archive_path = os.environ.get("ARCHIVE", "")
entry = os.environ["PAGE"].strip().lstrip("./")
paper_size = os.environ["SIZE"].strip()
margin = os.environ["MARGIN"].strip()

if not archive_path or not os.path.exists(archive_path):
    print(f"Error: Archive file '{archive_path}' does not exist", file=sys.stderr)
    sys.exit(1)

work_dir = tempfile.mkdtemp(prefix="bundle_page_")


def is_safe_path(base_dir, target_path):
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    return os.path.commonpath([abs_base, abs_target]) == abs_base


try:
    # 1. Unpack archive
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tar:
            for member in tar.getmembers():
                if is_safe_path(work_dir, os.path.join(work_dir, member.name)):
                    tar.extract(member, work_dir)
    elif zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(work_dir)
    else:
        print(f"Error: File '{archive_path}' is not a recognized tar or zip archive", file=sys.stderr)
        sys.exit(1)

    # 2. Locate the entry page. A bundle made with `tar -C dir .` lands files at
    #    the root; one made from a parent dir lands them one level down -- accept both.
    page_path = os.path.join(work_dir, entry)
    if not os.path.isfile(page_path):
        candidates = [
            os.path.join(root, entry)
            for root, _, files in os.walk(work_dir)
            if entry in files
        ]
        if len(candidates) == 1:
            page_path = candidates[0]
        else:
            held = sorted(
                os.path.relpath(os.path.join(r, f), work_dir)
                for r, _, fs in os.walk(work_dir) for f in fs if not f.startswith('._')
            )
            print(f"Error: page '{entry}' not found in the bundle; it holds: {', '.join(held) or '(nothing)'}", file=sys.stderr)
            sys.exit(1)
    page_dir = os.path.dirname(page_path)

    # 3. Build the document. Markdown gets converted and a minimal wrapper; HTML is
    #    used exactly as given. Either way the only CSS this tool adds is the page box.
    with open(page_path, "r", encoding="utf-8") as f:
        source = f.read()

    if page_path.lower().endswith((".html", ".htm")):
        body = source
    else:
        body = markdown.markdown(source, extensions=["extra", "tables"])

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: {paper_size}; margin: {margin}; }}
  body {{ margin: 0; }}
  img {{ max-width: 100%; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    # Rendered next to the page so relative src/href in the bundle resolve as-is.
    render_path = os.path.join(page_dir, "_render.html")
    with open(render_path, "w", encoding="utf-8") as f:
        f.write(document)

    output_path = "/output/document.pdf"
    if not os.path.exists("/output"):
        output_path = "document.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{render_path}", wait_until="load")
        page.pdf(
            path=output_path,
            format=paper_size,
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": margin, "bottom": margin, "left": margin, "right": margin},
        )
        browser.close()

    size = os.path.getsize(output_path)
    print(f"Rendered {entry} ({size:,} bytes) -> document.pdf")

finally:
    shutil.rmtree(work_dir, ignore_errors=True)
