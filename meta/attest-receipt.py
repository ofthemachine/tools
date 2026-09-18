#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Attest a fragletc run receipt (fraglet-receipt/2) the way OKF's Attested Computation attester does -- deterministic, no re-execution -- and report VERDICT: ATTESTED or VERDICT: REJECTED with every reason. Checks that the computation that ran is the sanctioned script (procedure_hash equals sha256 of the computation file, or the expected hash), that the receipt is internally consistent (memo_key recomputes from its own procedure_hash, params, and inputs under fragletc's documented formula, so an edited params field fails), that any claimed params match, that the run succeeded, and that an artifact claimed to be an output of the run hashes to what the receipt recorded.
#: when=Use when a result (a number, a phrase, an image) claims to have come from a tool run and you need to confirm the run was the sanctioned script with those parameters, or when checking the receipts bundled with a Daily Fraglet edition.
#: network=none
#: stdin=none
#: param=receipt:required:file:d=The fragletc --receipt JSON to attest
#: param=computation:file:d=The sanctioned script the run must have executed (its sha256 must equal the receipt's procedure_hash)
#: param=procedure_hash:d=Expected procedure_hash (sha256:<hex>), for when the script file is not at hand
#: param=params:d=Claimed parameters as key=value pairs separated by |, e.g. location=Edmonton|day=0; each must match the receipt exactly
#: param=artifact:file:d=A file claimed to be one of the run's outputs (a figure, a document); its sha256 must appear in the receipt's outputs
#: param=artifact_name:d=Which declared output the artifact claims to be (a relpath under /output); omitted, any output may match
import hashlib
import json
import os
import sys


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def memo_key_v2(procedure_hash, params, inputs):
    # fragletc's documented memo key formula (fraglet/pkg/receipt), byte-identical:
    # params and inputs merge into one sorted "lower(key):value" space.
    merged = {**params, **inputs}
    pairs = [f"{k.lower()}:{merged[k]}" for k in sorted(merged)]
    combined = procedure_hash + "\n" + "" + "\n" + "\n".join(pairs) + "\n"
    return "sha256:" + hashlib.sha256(combined.encode("utf-8")).hexdigest()


receipt_path = os.environ["RECEIPT"]
computation = os.environ.get("COMPUTATION", "").strip()
expected_hash = os.environ.get("PROCEDURE_HASH", "").strip()
claimed_raw = os.environ.get("PARAMS", "").strip()
artifact = os.environ.get("ARTIFACT", "").strip()
artifact_name = os.environ.get("ARTIFACT_NAME", "").strip()

try:
    with open(receipt_path, "r", encoding="utf-8") as f:
        r = json.load(f)
except (OSError, ValueError) as e:
    print(f"Error: cannot read receipt: {e}", file=sys.stderr)
    sys.exit(2)

reasons = []

# 1. A receipt shape this attester understands.
if r.get("schema") != "fraglet-receipt/2":
    reasons.append(f"schema is {r.get('schema')!r}, expected fraglet-receipt/2")
    print("VERDICT: REJECTED")
    for reason in reasons:
        print(f"- {reason}")
    sys.exit(1)

# 2. The computation that ran is the sanctioned one.
if computation:
    expected_hash = sha256_file(computation)
if expected_hash:
    if r.get("procedure_hash") != expected_hash:
        reasons.append(f"procedure_hash {r.get('procedure_hash')} is not the sanctioned computation {expected_hash}")
else:
    reasons.append("no computation or procedure_hash supplied: cannot confirm which script ran")

# 3. Nothing was bound outside the declared parameters. A conformant
#    invocation -- no positional args, no -e environment, stdin recorded --
#    is the only kind whose memo key is an honest identity, and the only
#    kind fragletc gives one to.
unbound = []
if r.get("argv"):
    unbound.append(f"positional arguments {r['argv']!r} were bound outside the declared parameters")
if r.get("env"):
    unbound.append(f"-e environment {r['env']!r} was bound outside the declared parameters")
if r.get("stdin_mode") == "stream":
    unbound.append("stdin was streamed, never recorded")
reasons.extend(unbound)

# 4. The receipt is internally consistent: its key recomputes from its own fields.
if "memo_key" not in r:
    if not unbound:
        reasons.append("receipt has no memo_key")
else:
    recomputed = memo_key_v2(r.get("procedure_hash", ""), r.get("params") or {}, r.get("inputs") or {})
    if recomputed != r["memo_key"]:
        reasons.append("memo_key does not recompute from procedure_hash + params + inputs: the receipt was edited")

# 5. Claimed parameters are the ones that ran.
if claimed_raw:
    recorded = r.get("params") or {}
    for pair in claimed_raw.split("|"):
        if "=" not in pair:
            reasons.append(f"claimed param {pair!r} is not key=value")
            continue
        k, v = pair.split("=", 1)
        if k not in recorded:
            reasons.append(f"claimed param {k!r} was not passed to the run")
        elif recorded[k] != v:
            reasons.append(f"claimed {k}={v!r} but the run used {k}={recorded[k]!r}")

# 6. The run succeeded.
if r.get("exit_code", 1) != 0:
    reasons.append(f"run exited {r.get('exit_code')}: its outputs are not a result")

# 7. The artifact is what the run produced.
if artifact:
    outputs = r.get("outputs") or {}
    got = sha256_file(artifact)
    if artifact_name:
        if artifact_name not in outputs:
            reasons.append(f"receipt has no output named {artifact_name!r}")
        elif outputs[artifact_name] != got:
            reasons.append(f"artifact hashes to {got}, receipt recorded {outputs[artifact_name]} for {artifact_name!r}")
    elif got not in outputs.values():
        reasons.append(f"artifact hashes to {got}, which is not among the receipt's outputs")

verdict = "ATTESTED" if not reasons else "REJECTED"
print(f"VERDICT: {verdict}")
print(f"procedure: {r.get('procedure', '?')} ({r.get('procedure_hash', '?')})")
# Execution class is not stored in a receipt; it is a predicate over the invocation
# (fraglet receipt.Invocation.Class): hermetic iff conformant, network=none, and a
# digest-pinned image, so the invocation alone determines the outputs.
hermetic = not unbound and "memo_key" in r and r.get("network") == "none" and "@sha256:" in r.get("image", "")
print(f"execution_class: {'hermetic' if hermetic else 'environmental'}  memo_key: {r.get('memo_key', '-')}")
for reason in reasons:
    print(f"- {reason}")
sys.exit(0 if not reasons else 1)
