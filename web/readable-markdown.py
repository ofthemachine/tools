#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Extract clean, readable Markdown article text from any web page using Trafilatura, stripping ads, navigations, sidebars, and boilerplate.
#: when=Use when the user wants the article text of a web page, or a page must be read without ads, navigation, and boilerplate.
#: network=required
#: stdin=none
#: param=url:required:d=Page URL to extract
#: output=article.md
import os
import sys
import urllib.request
import trafilatura

url = os.environ.get("URL", "").strip()
if not url:
    print("Error: URL parameter is required", file=sys.stderr)
    sys.exit(1)

req = urllib.request.Request(
    url,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    },
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        html_content = resp.read().decode("utf-8", errors="replace")
except Exception as e:
    print(f"Error fetching URL '{url}': {e}", file=sys.stderr)
    sys.exit(1)

extracted = trafilatura.extract(
    html_content,
    include_links=True,
    include_images=True,
    include_tables=True,
    output_format="markdown",
    url=url,
)

if not extracted or not extracted.strip():
    # Fallback to basic text extraction if trafilatura finds no main body article
    extracted = trafilatura.html2txt(html_content)

if not extracted or not extracted.strip():
    extracted = f"# {url}\n\n*No readable article body could be extracted from this page.*"

# Write to output file if /output exists, otherwise write to stdout or article.md
output_path = "/output/article.md"
if not os.path.exists("/output"):
    output_path = "article.md"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(extracted)

print(f"Extracted readable markdown ({len(extracted)} chars) -> article.md")
