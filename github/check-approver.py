#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Whether a GitHub event's sender is an approver -- one of the people allowed to say "go" to an automated action -- printed as one line naming who approved what, or a failure giving the reason. The approvers file lists one GitHub username per line (# comments; a leading @ or "- " is ignored, so a plain YAML list also works); matching ignores case. label=<name> also requires the event to be that label being applied, so only that label counts as approval. Its receipt is the approval record: which event, which list, which verdict.
#: when=Use when an issue-driven workflow must act only on approval from specific people -- e.g. before generating anything for a labelled issue, check that whoever applied the label is one of the repository's approvers.
#: network=none
#: stdin=none
#: param=event:required:file:d=GitHub event JSON, e.g. $GITHUB_EVENT_PATH for an issues.labeled event
#: param=approvers:required:file:d=The approvers: one GitHub username per line, # comments allowed
#: param=label:d=If set, the event must be this label being applied (e.g. poem:ready)
import json
import os
import re
import sys


def deny(reason):
    print(f"not approved: {reason}")
    sys.exit(1)


event = json.load(open(os.environ["EVENT"], encoding="utf-8"))
approvers = set()
for n, line in enumerate(open(os.environ["APPROVERS"], encoding="utf-8"), 1):
    name = line.split("#", 1)[0].strip().removeprefix("- ").strip().lstrip("@")
    if not name:
        continue
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", name):
        print(f"Error: approvers line {n}: {name!r} is not a GitHub username", file=sys.stderr)
        sys.exit(2)
    approvers.add(name.lower())
if not approvers:
    print("Error: the approvers file names nobody", file=sys.stderr)
    sys.exit(2)

sender = (event.get("sender") or {}).get("login") or ""
action = event.get("action") or "?"
label = (event.get("label") or {}).get("name")
issue = event.get("issue") or event.get("pull_request") or {}
target = f"#{issue.get('number')}" if issue.get("number") is not None else "(no issue)"

want = os.environ.get("LABEL", "")
if want and not (action == "labeled" and label == want):
    deny(f"event is {action} {label or ''} on {target}, not the {want} label being applied".replace("  ", " "))
if not sender:
    deny("event has no sender")
if sender.lower() not in approvers:
    deny(f"{sender} is not an approver ({action} {label or ''} on {target})".replace("  ", " "))

what = f"{action} {label}" if label else action
print(f"approved: {sender} {what} on {target} at {issue.get('updated_at') or 'unknown time'}")
