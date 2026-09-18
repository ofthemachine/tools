#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:f79c496c6737113c0f6e2d648474a67fb1a416fa34c22220d5714d0b7c6a6036
#: d=Render a webpage to a PDF (headless Chromium via Playwright) -- the print-to-PDF cousin of web/screenshot.py. Pass headers=<json object> to render a page behind auth, same as screenshot.py's own headers param.
#: when=Use when the user wants a PDF of a web page as the browser would print it, including layout and images.
#: network=required
#: stdin=none
#: param=url:required:d=Page URL to render
#: param=headers:d=JSON object of extra HTTP headers (e.g. Authorization)
#: output=page.pdf
import json
import os
import sys

from playwright.sync_api import sync_playwright

url = os.environ["URL"]
headers_raw = os.environ.get("HEADERS", "")

headers = {}
if headers_raw:
    try:
        headers = json.loads(headers_raw)
    except json.JSONDecodeError as e:
        print(f"headers param is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800}, extra_http_headers=headers)
    page = context.new_page()
    try:
        page.goto(url, wait_until="load", timeout=30_000)
        page.pdf(path="/output/page.pdf", print_background=True)
    except Exception as e:
        print(f"pdf render failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        browser.close()

print(f"Rendered PDF of {url} -> page.pdf")
