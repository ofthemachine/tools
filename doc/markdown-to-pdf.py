#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:8ac6f2f481f40e32a0b2f8dd7a834fd03197b1556bd8f55b1f167cd71d4877b0
#: d=Render Markdown text or a Markdown file into a high-quality reader-mode PDF using headless Chromium and clean typography styling.
#: when=Use when the user wants a PDF of some Markdown text or a single Markdown file with clean reader typography.
#: network=none
#: stdin=buffer
#: param=markdown_source:file:d=Host Markdown file mounted at /input/markdown_source
#: param=content:d=Inline Markdown text (or pipe stdin)
#: output=document.pdf
import os
import sys
import tempfile
import markdown
from playwright.sync_api import sync_playwright

source_path = os.environ.get("MARKDOWN_SOURCE", "")
content = os.environ.get("CONTENT", "")

md_text = ""
if source_path and os.path.exists(source_path):
    with open(source_path, "r", encoding="utf-8") as f:
        md_text = f.read()
elif content:
    md_text = content
elif not sys.stdin.isatty():
    md_text = sys.stdin.read()

if not md_text or not md_text.strip():
    print("Error: No markdown provided via MARKDOWN_SOURCE, CONTENT, or stdin", file=sys.stderr)
    sys.exit(1)

html_body = markdown.markdown(
    md_text,
    extensions=["extra", "codehilite", "tables", "toc"],
)

styled_html = f"""<!DOCTYPE html>
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
    color: #1a202c;
    background-color: #ffffff;
    max-width: 800px;
    margin: 0 auto;
    font-size: 11pt;
  }}
  h1, h2, h3, h4, h5, h6 {{
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
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

output_path = "/output/document.pdf"
if not os.path.exists("/output"):
    output_path = "document.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content(styled_html, wait_until="load")
    page.pdf(
        path=output_path,
        format="A4",
        print_background=True,
        margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
    )
    browser.close()

print(f"Rendered Markdown to PDF -> document.pdf")
