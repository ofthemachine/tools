#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:59784cff1945b7d6093a591b5e5292b8c989f0691af0494fbbe1c6b8083a16cb
#: d=The lead summary of the Wikipedia article that best matches a phrase (Wikipedia's own search, then its page summary), written to summary.md as its title, link and a few paragraphs. A phrase nothing matches still succeeds, and summary.md says no article was found, so a workflow that cites it goes on with no evidence rather than stopping. Unlike web/page-to-markdown it needs no URL, only words.
#: when=Use when a workflow step needs encyclopedic background on a subject named in plain words -- a topic, a dish, a person, a dispute -- as a file a later step reads.
#: network=required
#: stdin=none
#: param=query:required:d=What to look up, in plain words, e.g. pineapple on pizza
#: param=language:default=en:d=Wikipedia language code, e.g. en, fr, de
#: param=max_bytes:default=3000:d=At most this many bytes of the summary's text
#: output=summary.md
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "ofthemachine-tools/1 (https://github.com/ofthemachine/tools)"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


query = os.environ["QUERY"].strip()
lang = os.environ["LANGUAGE"].strip()
limit = int(os.environ["MAX_BYTES"])
if not lang.isalpha():
    print(f"Error: language {lang!r} is not a language code", file=sys.stderr)
    sys.exit(2)
base = f"https://{lang}.wikipedia.org"

try:
    found = get(base + "/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query, "srlimit": 1, "format": "json"}))
    hits = found.get("query", {}).get("search", [])
    if not hits:
        text = f"# No article found\n\nWikipedia has no article matching \"{query}\".\n"
        title = None
    else:
        title = hits[0]["title"]
        page = get(base + "/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe=""))
        extract = page.get("extract", "").strip()
        if len(extract.encode()) > limit:
            extract = extract.encode()[:limit].decode("utf-8", "ignore").rsplit(" ", 1)[0] + " …"
        link = page.get("content_urls", {}).get("desktop", {}).get("page", base + "/wiki/" + urllib.parse.quote(title))
        text = f"# {page.get('title', title)}\n\n{link}\n\n{extract}\n"
except (urllib.error.URLError, ValueError, KeyError) as e:
    print(f"Error: Wikipedia lookup failed: {e}", file=sys.stderr)
    sys.exit(1)

os.makedirs("/output", exist_ok=True)
with open("/output/summary.md", "w", encoding="utf-8") as f:
    f.write(text)
print(f"wikipedia: {title}" if title else f"wikipedia: no article for {query!r}")
