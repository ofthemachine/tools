#!/usr/bin/env -S fragletc --image ofthemachine/headless-browser@sha256:f79c496c6737113c0f6e2d648474a67fb1a416fa34c22220d5714d0b7c6a6036
#: d=Capture a full-page PNG screenshot of a webpage (headless Chromium via Playwright). Pass headers=<json object> to screenshot a page behind auth (e.g. headers={"Authorization":"Bearer <token>"}) -- a plain browser navigation can't set custom headers. settle_ms (default 2000) is an extra wait after page load, for pages whose real content only appears after their own async JS runs.
#: when=Use when the user wants a picture of a rendered page, or a visual check of a URL rather than its text.
#: network=required
#: stdin=none
#: param=url:required:d=Page URL to capture
#: param=headers:d=JSON object of extra HTTP headers (e.g. Authorization)
#: param=settle_ms:default=2000:description=Extra wait after page load for async JS content
#: output=page.png
import json
import os
import sys

from playwright.sync_api import sync_playwright

url = os.environ["URL"]
headers_raw = os.environ.get("HEADERS", "")
settle_ms = int(os.environ["SETTLE_MS"])

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
        if settle_ms > 0:
            page.wait_for_timeout(settle_ms)
        page.screenshot(path="/output/page.png", full_page=True)
    except Exception as e:
        print(f"screenshot failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        browser.close()

print(f"Captured screenshot of {url} -> page.png")
