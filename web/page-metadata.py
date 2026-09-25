#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Fetch a URL and extract its <title> and Open Graph tags (og:title, og:description, og:image) -- stdlib html.parser only, no external service.
#: when=Use when the user wants a page's title, description, or preview image, or a link needs a caption without fetching the whole article.
#: network=required
#: stdin=none
#: param=url:required:d=Page URL to fetch
import html.parser
import os
import sys
import urllib.request


class MetaParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.og = {}
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            d = dict(attrs)
            prop = d.get("property", "")
            if prop.startswith("og:") and d.get("content"):
                self.og[prop] = d["content"]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()


url = os.environ["URL"]
req = urllib.request.Request(url, headers={"User-Agent": "ofthemachine-tools (https://github.com/ofthemachine/tools)"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read(1_000_000).decode("utf-8", "replace")
except Exception as e:
    print(f"fetch failed: {e}", file=sys.stderr)
    sys.exit(1)

parser = MetaParser()
parser.feed(body)

print(f"Title: {parser.title or ''}")
print(f"Og Title: {parser.og.get('og:title', '')}")
print(f"Og Description: {parser.og.get('og:description', '')}")
print(f"Og Image: {parser.og.get('og:image', '')}")
