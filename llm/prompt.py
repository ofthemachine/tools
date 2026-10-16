#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Compose the two files an LLM step reads, prompt.md (task, subject, reference text, constraints) and system.md (voice or house style, examples), from plain params and optional files, so a plan can hand an earlier step's output to llm/cohere as an inspectable artifact instead of string-building a prompt.
#: when=Use as the step before llm/cohere when a request must combine a task with text produced earlier (headlines, a transcript, a document) or with a stored style guide, or whenever the prompt itself should carry a receipt.
#: network=none
#: stdin=none
#: param=task:required:d=What the model must produce, in one or two sentences
#: param=subject:default=:d=What it is about, with the concrete names, numbers and events to keep
#: param=context:default=:d=Reference text to work from, inline (typically an earlier step's output); use context_file for a file
#: param=context_file:file:d=Reference text to work from, as a file
#: param=context_label:default=Reference material:d=Heading placed above the reference text in prompt.md
#: param=constraints:default=:d=Hard requirements such as length, form or things to avoid; newline- or semicolon-separated
#: param=style:default=:d=The voice or house style, inline, for system.md; use style_file for a file
#: param=style_file:file:d=The voice or house style, as a file, for system.md
#: param=examples_file:file:d=Examples of the wanted output, appended to system.md under an Examples heading
#: output=prompt.md
#: output=system.md
import os
import pathlib
import re


def text_of(inline_var, file_var):
    """An inline param wins; else the mounted file's text; else empty."""
    inline = os.environ.get(inline_var, "").strip()
    if inline:
        return inline
    path = os.environ.get(file_var, "")
    if path and os.path.exists(path):
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace").strip()
    return ""


def bullets(raw):
    items = [s.strip() for s in re.split(r"[;\n]+", raw) if s.strip()]
    return "\n".join("- " + s for s in items)


task = os.environ["TASK"].strip()
subject = os.environ["SUBJECT"].strip()
context = text_of("CONTEXT", "CONTEXT_FILE")
label = os.environ["CONTEXT_LABEL"].strip() or "Reference material"
constraints = bullets(os.environ["CONSTRAINTS"])
style = text_of("STYLE", "STYLE_FILE")
examples = text_of("", "EXAMPLES_FILE")

parts = ["# Task", task]
if subject:
    parts += ["", "## Subject", subject]
if context:
    parts += ["", f"## {label}", context]
if constraints:
    parts += ["", "## Constraints", constraints]
prompt = "\n".join(parts).strip() + "\n"

system = style or "You are a careful writer. Do exactly the task in the prompt, keeping every fact it gives you, and return only the finished piece."
if examples:
    system = system.rstrip() + "\n\n## Examples\n" + examples
system = system.rstrip() + "\n"

pathlib.Path("/output/prompt.md").write_text(prompt, encoding="utf-8")
pathlib.Path("/output/system.md").write_text(system, encoding="utf-8")
print(f"prompt.md {len(prompt.split())} words; system.md {len(system.split())} words"
      + ("; context from " + ("param" if os.environ.get("CONTEXT", "").strip() else "file") if context else "; no context"))
