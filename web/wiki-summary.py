#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:59784cff1945b7d6093a591b5e5292b8c989f0691af0494fbbe1c6b8083a16cb
#: d=The lead summaries of the Wikipedia articles that best match one or more topics (Wikipedia's own search, then each article's page summary), written to summary.md as each article's title, link and a few paragraphs. Topics are separated by semicolons (cat behavior; object permanence) and share the byte budget. An article whose title shares no word with its topic is not taken (a search for a sentence finds noise), so a topic may find nothing; a query nothing matches still succeeds, and summary.md says no article was found, so a workflow that cites it goes on with no evidence rather than stopping. A rate limit or a server error exits 75 (temporary: fragletc --retry). Unlike web/page-to-markdown it needs no URL, only words.
#: when=Use when a workflow step needs encyclopedic background on subjects named in a few plain words -- a topic, a dish, a person -- as a file a later step reads. Name subjects, not sentences: "cat behavior", not "cats who knock things off tables".
#: network=required
#: stdin=none
#: param=query:required:d=What to look up: a topic in a few plain words, or several separated by semicolons, e.g. cat behavior; object permanence
#: param=language:default=en:d=Wikipedia language code, e.g. en, fr, de
#: param=max_bytes:default=3000:d=At most this many bytes of summary text in all, shared by the topics
#: output=summary.md
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "ofthemachine-tools/1 (https://github.com/ofthemachine/tools)"}
STOP = {"the", "and", "for", "with", "who", "that", "this", "from", "into", "off", "are", "was", "list"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def words(text):
    """Content words, a plural's s dropped: what a title must share with its topic."""
    out = set()
    for w in re.findall(r"[^\W\d_]{3,}", text.lower()):
        if w not in STOP:
            out.add(w[:-1] if w.endswith("s") and len(w) > 3 else w)
    return out


def article(base, topic, taken):
    """The first of the top hits whose title shares a word with topic and is not taken."""
    found = get(base + "/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": topic, "srlimit": 3, "format": "json"}))
    want = words(topic)
    for hit in found.get("query", {}).get("search", []):
        title = hit["title"]
        if title not in taken and want & words(title):
            return title
    return None


topics = [t.strip() for t in os.environ["QUERY"].replace("\n", ";").split(";") if t.strip()][:5]
lang = os.environ["LANGUAGE"].strip()
limit = int(os.environ["MAX_BYTES"])
if not topics:
    print("Error: query names no topic", file=sys.stderr)
    sys.exit(2)
if not lang.isalpha():
    print(f"Error: language {lang!r} is not a language code", file=sys.stderr)
    sys.exit(2)
base = f"https://{lang}.wikipedia.org"

sections, titles = [], []
try:
    for topic in topics:
        title = article(base, topic, titles)
        if title:
            titles.append(title)
    share = limit // max(len(titles), 1)
    for title in titles:
        page = get(base + "/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe=""))
        extract = page.get("extract", "").strip()
        if len(extract.encode()) > share:
            extract = extract.encode()[:share].decode("utf-8", "ignore").rsplit(" ", 1)[0] + " …"
        link = page.get("content_urls", {}).get("desktop", {}).get("page", base + "/wiki/" + urllib.parse.quote(title))
        sections.append(f"# {page.get('title', title)}\n\n{link}\n\n{extract}\n")
except urllib.error.HTTPError as e:
    print(f"Error: Wikipedia returned HTTP {e.code}", file=sys.stderr)
    # EX_TEMPFAIL: a rate limit or a server error may pass (fragletc --retry)
    sys.exit(75 if e.code == 429 or e.code >= 500 else 1)
except (urllib.error.URLError, TimeoutError) as e:
    print(f"Error: Wikipedia lookup failed: {e}", file=sys.stderr)
    sys.exit(75)
except (ValueError, KeyError) as e:
    print(f"Error: Wikipedia lookup failed: {e}", file=sys.stderr)
    sys.exit(1)

text = "\n".join(sections) if sections else "# No article found\n\nWikipedia has no article matching \"" + "; ".join(topics) + "\".\n"
os.makedirs("/output", exist_ok=True)
with open("/output/summary.md", "w", encoding="utf-8") as f:
    f.write(text)
print("wikipedia: " + ("; ".join(titles) if titles else "no article for " + repr("; ".join(topics))))
