#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Search the web through DuckDuckGo and print one "title<TAB>url<TAB>snippet" result per line, with no API key required. Set site to constrain results to a single domain, timelimit to d, w, m, or y for recency, and region for locale-weighted results. Pairs with readable-markdown to turn a query into full article text.
#: when=Use when the user wants web search results, recent news about a topic or place, or pages from a specific site, and no API key is available.
#: network=required
#: stdin=none
#: param=query:required:d=Search query
#: param=max_results:default=10:d=Maximum results to print
#: param=site:d=Restrict results to this domain
#: param=region:default=wt-wt:description=DuckDuckGo region code (wt-wt = worldwide)
#: param=timelimit:d=Recency filter: d, w, m, or y
import os
import sys

from ddgs import DDGS

query = os.environ.get("QUERY", "").strip()
site = os.environ.get("SITE", "").strip()
region = os.environ["REGION"].strip()
timelimit = os.environ.get("TIMELIMIT", "").strip() or None

if not query:
    print("Error: query parameter is empty", file=sys.stderr)
    sys.exit(1)

try:
    max_results = int(os.environ["MAX_RESULTS"])
except ValueError:
    print(f"Error: max_results must be an integer, got '{os.environ.get('MAX_RESULTS')}'", file=sys.stderr)
    sys.exit(1)

if site:
    query = f"{query} site:{site}"

try:
    results = list(DDGS().text(query, region=region, timelimit=timelimit, max_results=max_results))
except Exception as e:
    print(f"search failed: {e}", file=sys.stderr)
    sys.exit(1)

if not results:
    print(f"no results for {query!r}", file=sys.stderr)
    sys.exit(1)

for item in results:
    title = (item.get("title") or "").strip()
    url = (item.get("href") or item.get("url") or "").strip()
    snippet = " ".join((item.get("body") or "").split())
    print(f"{title}\t{url}\t{snippet}")
