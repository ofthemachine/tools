#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=One chat completion from a local, OpenAI-compatible model server (LM Studio, llama.cpp, Ollama) from a prompt file and an optional system prompt file, written to response.md; no key. With think=false a reasoning model is asked to answer at once (an empty think block is prefilled), and any think block left in the answer is removed. stdout is a one-line summary, never the completion.
#: when=Use when a workflow step needs text from a language model running on this machine (LM Studio, llama.cpp, Ollama): no key, no cloud.
#: network=required
#: stdin=none
#: param=prompt:file:d=Prompt file (the user message)
#: param=prompt_text:d=Inline prompt, when there is no prompt file
#: param=system:file:d=System prompt file
#: param=model:required:d=The model's id on the server, e.g. qwen/qwen3.8-27b
#: param=endpoint:d=The server's chat completions URL as the container reaches it; empty: LM Studio on this machine (host.docker.internal, port 11234)
#: param=temperature:default=0.7:d=Sampling temperature
#: param=seed:default=42:d=Sampling seed
#: param=max_tokens:default=400:d=Most tokens to generate
#: param=think:default=false:kind=bool:d=Let a reasoning model think before it answers
#: param=timeout:default=900:kind=integer:d=Seconds to wait for the answer: a local server may be busy with another agent's call, or loading the model
#: output=response.md
import json
import os
import re
import sys
import urllib.error
import urllib.request

TEMPFAIL = 75  # a server error or a dropped connection may pass (fragletc --retry)


def fail(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


prompt = open(os.environ["PROMPT"], encoding="utf-8").read() if os.environ.get("PROMPT") else os.environ.get("PROMPT_TEXT", "")
if not prompt.strip():
    fail("no prompt: pass prompt=<file> or prompt_text=<text>")
messages = []
if os.environ.get("SYSTEM"):
    messages.append({"role": "system", "content": open(os.environ["SYSTEM"], encoding="utf-8").read()})
messages.append({"role": "user", "content": prompt})
if os.environ.get("THINK", "false").lower() not in ("true", "1", "yes"):
    messages.append({"role": "assistant", "content": "<think>\n\n</think>\n\n"})
body = {"model": os.environ["MODEL"], "messages": messages, "temperature": float(os.environ["TEMPERATURE"]),
        "seed": int(os.environ["SEED"]), "max_tokens": int(os.environ["MAX_TOKENS"])}
endpoint = os.environ.get("ENDPOINT", "").strip() or "http://host.docker.internal:11234/v1/chat/completions"
req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=int(os.environ.get("TIMEOUT") or 900)) as resp:
        res = json.load(resp)
except urllib.error.HTTPError as e:
    fail(f"the model server returned HTTP {e.code}: {e.read(300).decode('utf-8', 'replace')}", TEMPFAIL if e.code >= 500 else 1)
except (urllib.error.URLError, TimeoutError) as e:
    fail(f"the model server did not answer: {e}", TEMPFAIL)
choice = (res.get("choices") or [{}])[0]
text = re.sub(r"<think>.*?</think>", "", (choice.get("message") or {}).get("content") or "", flags=re.S).strip()
if not text:
    fail(f"no text in the answer: {json.dumps(res)[:300]}")
os.makedirs("/output", exist_ok=True)
with open("/output/response.md", "w", encoding="utf-8") as f:
    f.write(text + "\n")
usage = res.get("usage") or {}
print(f"{res.get('model', body['model'])}: {usage.get('prompt_tokens', '?')} in, {usage.get('completion_tokens', '?')} out, {choice.get('finish_reason', '?')}")
