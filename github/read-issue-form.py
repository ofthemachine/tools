#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=The fields of a GitHub issue form as JSON: {"issue": {number, title, author, url, labels}, "fields": {<label_slug>: value}}. GitHub renders a form submission as "### Label" headings with values beneath; each heading becomes a snake_case key, "_No response_" becomes null, and checkbox lists become arrays of the checked options. Accepts a whole GitHub event payload (issues/issue_comment, e.g. $GITHUB_EVENT_PATH) or a bare issue body.
#: when=Use when an issue-driven workflow needs the answers from a templated GitHub issue as structured data, e.g. turning a labelled request issue into a request.json for the next step.
#: network=none
#: stdin=none
#: param=issue:required:file:d=GitHub event JSON (with .issue) or a bare issue body in Markdown
import json
import os
import re
import sys

raw = open(os.environ["ISSUE"], encoding="utf-8").read()

meta = {}
body = raw
try:
    event = json.loads(raw)
except ValueError:
    event = None
if isinstance(event, dict):
    issue = event.get("issue")
    if not isinstance(issue, dict):
        print("Error: JSON input has no .issue object; pass an issues/issue_comment event or a bare issue body", file=sys.stderr)
        sys.exit(1)
    body = issue.get("body") or ""
    meta = {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "author": (issue.get("user") or {}).get("login"),
        "url": issue.get("html_url"),
        "labels": [l.get("name") for l in issue.get("labels") or [] if isinstance(l, dict)],
    }


def slug(label):
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def value(text):
    text = text.strip()
    if text in ("", "_No response_"):
        return None
    boxes = re.findall(r"^- \[([ xX])\] (.+)$", text, re.M)
    if boxes and len(boxes) == len(text.splitlines()):
        return [opt.strip() for mark, opt in boxes if mark.lower() == "x"]
    return text


fields = {}
for block in re.split(r"^### ", body.replace("\r\n", "\n"), flags=re.M)[1:]:
    label, _, rest = block.partition("\n")
    key = slug(label)
    if key and key not in fields:
        fields[key] = value(rest)

if not fields:
    print("Error: no '### Label' sections found; is this an issue form submission?", file=sys.stderr)
    sys.exit(1)

print(json.dumps({"issue": meta, "fields": fields}, indent=2, ensure_ascii=False))
