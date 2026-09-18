#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:8ac6f2f481f40e32a0b2f8dd7a834fd03197b1556bd8f55b1f167cd71d4877b0
#: d=Extract an archive (tar, tar.gz, zip) containing multiple Markdown files and optional assets, compiling them into a unified, high-typography publication PDF with page breaks, table of contents, and embedded images.
#: when=Use when several Markdown files (optionally with images) should become one PDF publication with a table of contents and page breaks.
#: network=none
#: stdin=none
#: param=archive:required:file:d=tar/tar.gz/zip of Markdown files and optional assets
#: param=title:default=Document Digest:d=PDF document title
#: param=toc:default=true:d=Include a table of contents
#: output=digest.pdf
import os
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
import markdown
from playwright.sync_api import sync_playwright

archive_path = os.environ.get("ARCHIVE", "")
doc_title = os.environ["TITLE"].strip()
show_toc = os.environ["TOC"].strip().lower() in ("true", "1", "yes")

if not archive_path or not os.path.exists(archive_path):
    print(f"Error: Archive file '{archive_path}' does not exist", file=sys.stderr)
    sys.exit(1)

work_dir = tempfile.mkdtemp(prefix="md_digest_")

try:
    # 1. Unpack archive
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tar:
            def is_safe_path(base_dir, target_path):
                abs_base = os.path.abspath(base_dir)
                abs_target = os.path.abspath(target_path)
                return os.path.commonpath([abs_base, abs_target]) == abs_base

            for member in tar.getmembers():
                target = os.path.join(work_dir, member.name)
                if is_safe_path(work_dir, target):
                    tar.extract(member, work_dir)
    elif zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(work_dir)
    else:
        print(f"Error: File '{archive_path}' is not a recognized tar or zip archive", file=sys.stderr)
        sys.exit(1)

    # 2. Determine ordering of markdown files
    manifest_names = ["manifest.txt", "order.txt", "index.txt"]
    ordered_md_paths = []
    for mf in manifest_names:
        mf_path = os.path.join(work_dir, mf)
        if os.path.exists(mf_path):
            with open(mf_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        target = os.path.join(work_dir, line)
                        if os.path.exists(target):
                            ordered_md_paths.append(target)
            if ordered_md_paths:
                break

    if not ordered_md_paths:
        for root, _, files in os.walk(work_dir):
            for f in files:
                if f.endswith((".md", ".markdown")) and not f.startswith("."):
                    ordered_md_paths.append(os.path.join(root, f))
        ordered_md_paths.sort()

    if not ordered_md_paths:
        print("Error: No markdown (.md) files found in the archive", file=sys.stderr)
        sys.exit(1)

    # 3. Parse and convert markdown files
    sections_html = []
    toc_items = []

    for idx, md_path in enumerate(ordered_md_paths, 1):
        with open(md_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        content = raw_text
        meta_title = ""
        # Check for YAML frontmatter
        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                content = parts[2]
                for line in fm.splitlines():
                    if line.startswith("title:"):
                        meta_title = line.split(":", 1)[1].strip().strip('"').strip("'")

        # Fallback to first heading
        if not meta_title:
            for line in content.splitlines():
                line_s = line.strip()
                if line_s.startswith("# "):
                    meta_title = line_s.lstrip("# ").strip()
                    break

        if not meta_title:
            rel_name = os.path.relpath(md_path, work_dir)
            meta_title = os.path.splitext(os.path.basename(rel_name))[0].replace("-", " ").replace("_", " ").title()

        sec_id = f"section-{idx}"
        toc_items.append((sec_id, meta_title))

        rendered = markdown.markdown(
            content,
            extensions=["extra", "codehilite", "tables", "toc"],
        )

        sections_html.append(f"""
        <article class="doc-section" id="{sec_id}">
          {rendered}
        </article>
        """)

    # 4. Generate Table of Contents HTML
    toc_html = ""
    if show_toc and len(toc_items) > 1:
        toc_list_items = "".join([
            f'<li><a href="#{sec_id}">{title}</a></li>'
            for sec_id, title in toc_items
        ])
        toc_html = f"""
        <div class="toc-box">
          <h2>Contents</h2>
          <ul class="toc-list">
            {toc_list_items}
          </ul>
        </div>
        """

    # 5. Build full HTML document
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #1e293b;
    background-color: #ffffff;
    max-width: 820px;
    margin: 0 auto;
    font-size: 11pt;
  }}
  .cover-header {{
    margin-bottom: 2.5em;
    padding-bottom: 1.5em;
    border-bottom: 3px solid #0f172a;
  }}
  .cover-header h1 {{
    font-size: 26pt;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 0.2em 0;
    line-height: 1.15;
  }}
  .cover-header .meta {{
    font-size: 10pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }}
  .toc-box {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.2em 1.5em;
    margin-bottom: 2.5em;
  }}
  .toc-box h2 {{
    font-size: 12pt;
    color: #334155;
    margin-top: 0;
    margin-bottom: 0.8em;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: none;
    padding-bottom: 0;
  }}
  .toc-list {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  .toc-list li {{
    padding: 0.4em 0;
    border-bottom: 1px dashed #e2e8f0;
  }}
  .toc-list li:last-child {{
    border-bottom: none;
  }}
  .toc-list a {{
    color: #0f172a;
    text-decoration: none;
    font-weight: 500;
  }}
  .doc-section {{
    page-break-before: always;
  }}
  .doc-section:first-of-type {{
    page-break-before: auto;
  }}
  h1, h2, h3, h4 {{
    color: #0f172a;
    font-weight: 700;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    line-height: 1.25;
  }}
  h1 {{ font-size: 20pt; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.3em; }}
  h2 {{ font-size: 15pt; border-bottom: 1px solid #edf2f7; padding-bottom: 0.2em; }}
  h3 {{ font-size: 13pt; }}
  p {{ margin-bottom: 1em; text-align: justify; }}
  a {{ color: #2563eb; text-decoration: none; }}
  code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 9.5pt;
    background-color: #f1f5f9;
    padding: 0.15em 0.35em;
    border-radius: 4px;
    color: #0f172a;
  }}
  pre {{
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.45;
  }}
  pre code {{
    background-color: transparent;
    color: inherit;
    padding: 0;
  }}
  blockquote {{
    border-left: 4px solid #3b82f6;
    margin: 1.2em 0;
    padding-left: 1em;
    color: #475569;
    font-style: italic;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
  }}
  th, td {{
    border: 1px solid #cbd5e1;
    padding: 8px 12px;
    text-align: left;
    font-size: 10pt;
  }}
  th {{
    background-color: #f8fafc;
    font-weight: 600;
  }}
  img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.5em auto;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }}
</style>
</head>
<body>
  <div class="cover-header">
    <div class="meta">Briefing Digest</div>
    <h1>{doc_title}</h1>
  </div>
  {toc_html}
  {''.join(sections_html)}
</body>
</html>"""

    html_file = os.path.join(work_dir, "index.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    # 6. Render PDF with Playwright
    output_path = "/output/digest.pdf"
    if not os.path.exists("/output"):
        output_path = "digest.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(html_file)}", wait_until="load")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    print(f"Compiled {len(ordered_md_paths)} markdown document(s) -> digest.pdf")

finally:
    shutil.rmtree(work_dir, ignore_errors=True)
