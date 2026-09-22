---
type: Testing Strategy
title: Fraglet Testing Strategy for ofthemachine/tools
date: 2026-09-21
---

# Fraglet Testing Strategy

## Context

The `ofthemachine/tools` catalog contains **level-0 fraglets**: single-file, hermetic (or network-required), containerized scripts with declared input/output contracts. Unlike traditional code repositories, testing fraglets requires:

1. **Container invocation overhead** — each test runs inside a pinned Docker image via `fragletc`
2. **No side effects** — fraglets are pure functions (hermetic) or stateless external queries (network)
3. **Receipt-based verification** — outputs are validated via content hashes and execution receipts
4. **Determinism** — hermetic tools must produce identical outputs for identical inputs (memo-key stability)

## Testing Philosophy

**Every fraglet test answers three questions:**
1. **Does it run?** (Contract conformance: required params present, exit code 0, declared outputs written)
2. **Does it produce the right shape?** (Output format correctness: valid JSON, valid CSV, valid SVG)
3. **Is the computation correct?** (Semantic correctness: results match expected values or behaviors)

Tests should be **runnable offline** (no dependency on external APIs except network-required tools) and **memoizable** — a passing run's receipt should have a stable `memo_key` so re-runs are cached.

---

## Testing Patterns by Tool Type

### Pattern 1: Pure Computation Tools (network=none)

**Examples:** `chart/plot.py`, `data/table-query.py`, `sheet/inspect.py`

These are hermetic and deterministic. A test:
1. Prepares fixture data (CSV, JSON, XLSX file)
2. Runs the fraglet via `fragletc --receipt <output.json>`
3. Validates:
   - Exit code is 0
   - Declared outputs exist and are non-empty
   - Output format is valid (JSON parses, CSV reads, SVG is well-formed)
   - `memo_key` in receipt is non-empty (proof of conformance)
   - Re-running with same input produces identical `memo_key` (determinism)

**Test fixture strategy:**
- Store fixtures under `tests/fixtures/<pack>/` (e.g., `tests/fixtures/chart/sales.csv`)
- Keep fixtures small (< 1MB) for fast CI
- Include edge cases: empty data, single row, large numeric ranges, special characters in strings

**Receipt assertions:**
```json
{
  "memo_key": "sha256:...",              // must be non-empty (conformant run)
  "invocation": {
    "class": "hermetic",                 // must be hermetic for network=none tools
    "argv": [],                          // must be empty
    "env": []                            // must be empty
  },
  "exit_code": 0,                        // must be 0
  "outputs": {
    "chart.svg": "sha256:..."            // declared outputs must be present
  }
}
```

---

### Pattern 2: Network-Required Tools (network=required)

**Examples:** `net/registry-lookup.py`

These query live external APIs. Tests should:
1. **Mock or stub the network calls** where possible (e.g., fixture JSON responses from PyPI)
2. **Accept that memo_key varies** (live API responses are non-deterministic)
3. **Validate output shape and error handling** (e.g., package not found → graceful exit 1)

**Test fixture strategy:**
- Store fixture responses under `tests/fixtures/<pack>/responses/` (e.g., `tests/fixtures/net/pypi-requests-latest.json`)
- Mock via environment or local HTTP server (fragletc's `--network` override allows this)
- For CI, either skip network tests or mock them with VCR-style cassettes

**Receipt assertions:**
```json
{
  "memo_key": "",                        // will be empty (non-conformant due to live API)
  "invocation": {
    "class": "environmental",            // live network state, so not hermetic
    "network": "required"
  },
  "exit_code": 0                         // but still must exit cleanly on success
}
```

---

### Pattern 3: File-Mount Tools (param=<alias>:file)

**Examples:** `doc/pdf-to-images.py`, `sheet/convert.py`

These read host files. Tests:
1. Prepare a real file (PDF, XLSX, etc.) under `tests/fixtures/`
2. Run fragletc with `-p <alias>=<file>` mount
3. Validate output exists and has expected format

**Gotchas:**
- File mounts are read-only in the container, so can't test file write scenarios
- Path handling: use relative paths in test scripts for portability

---

### Pattern 4: Stdin Tools (stdin=buffer or stdin=stream)

**Examples:** `chart/plot.py` (inline CSV via stdin), `data/table-query.py` (inline SQL data)

These accept piped input. Tests:
1. Pipe fixture data via stdin (or use `-p <text_param>` for inline)
2. Validate `inputs[""]` (AnonKey) in receipt has the stdin hash

**Receipt assertions:**
```json
{
  "inputs": {
    "": "sha256:..."                     // stdin hash under empty key
  }
}
```

---

## Test Organization

### Directory Structure

```
tools/
  chart/
    index.md
    plot.py
    tests/
      test_plot.sh              # Main test harness
      fixtures/
        sales.csv              # Test data
        wide-data.csv          # Edge case: many columns
        empty.csv              # Edge case: no data
  data/
    tests/
      test_query.sh
      fixtures/
        employees.csv
        large-table.csv        # 10MB+ for performance testing
  (... one tests/ per pack)
```

### Test Runner Script

Each pack should have a `tests/test_<pack>.sh` that:

```bash
#!/bin/bash
# tests/test_chart.sh — run all chart tests

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
FIXTURES=$(pwd)/tests/fixtures
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing chart/plot.py..."

# Test 1: bar chart from CSV file
$FRAGLETC plot.py \
  -p data=$FIXTURES/sales.csv \
  -p type=bar \
  -p x=month \
  -p y=revenue \
  --output result.svg \
  --receipt $OUTPUT/bar.json
  
test -f $OUTPUT/result.svg || (echo "FAIL: no output file"; exit 1)
grep -q '<svg' $OUTPUT/result.svg || (echo "FAIL: not valid SVG"; exit 1)

# Test 2: line chart from JSON stdin
cat $FIXTURES/data.json | $FRAGLETC plot.py \
  -p type=line \
  -p x=label \
  -p y=value \
  --output result.svg \
  --receipt $OUTPUT/line.json

# Test 3: determinism — same input, same memo_key
MEMO1=$(jq -r '.memo_key' $OUTPUT/bar.json)
$FRAGLETC plot.py -p data=$FIXTURES/sales.csv -p type=bar -p x=month -p y=revenue --receipt $OUTPUT/bar2.json
MEMO2=$(jq -r '.memo_key' $OUTPUT/bar2.json)
test "$MEMO1" = "$MEMO2" || (echo "FAIL: non-deterministic (memo_keys differ)"; exit 1)

echo "✓ All chart tests passed"
```

---

## CI Integration

### GitHub Actions Example

```yaml
name: Test Fraglets
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: ofthemachine/setup-fragletc@v1
      - run: |
          cd tools
          for pack in chart data doc net sheet; do
            if [ -d "$pack/tests" ]; then
              bash "$pack/tests/test_$pack.sh" || exit 1
            fi
          done
      - run: make build   # Validate catalog compilation
```

---

## Lint + Compilation as Gating

The existing `make build` target already validates:
- `fragletc lint --strict` on every tool
- Catalog compilation (`meta/compile-catalog.py`)
- Generated `SKILL.md` format and size limits

This catches:
- Missing `when=` directives
- Undeclared params or outputs
- Invalid network/stdin declarations
- Script body that contradicts the header

**Fraglet linting is the first line of defense.** Supplement it with functional tests only where semantic correctness is at risk (e.g., SQL queries, chart rendering).

---

## Regression Testing

For each new tool or significant change:

1. **Add a fixture** to `tests/fixtures/<pack>/`
2. **Record a baseline receipt** (the "golden" memo_key and outputs)
3. **In CI, fail if memo_key changes** (indicates unintended behavioral change)
4. **For network tools, record fixture responses** and mock them in tests

---

## Testing Checklist (Pre-Merge)

Before a tool PR merges:

- [ ] `fragletc lint --strict <pack>/<tool>` passes
- [ ] `make build` compiles the catalog cleanly
- [ ] `tests/<pack>/test_<tool>.sh` passes locally
- [ ] Tool tested with edge cases (empty input, large input, special characters)
- [ ] Receipt validates: `exit_code=0`, `memo_key` non-empty, outputs present
- [ ] Hermetic tools produce stable `memo_key` on re-run
- [ ] Network tools handle 404/timeout gracefully (exit 1, stderr message)
- [ ] Output format is parseable (valid JSON/CSV/SVG/etc.)

---

## Known Gaps

1. **No integration test harness yet** — each pack defines its own `tests/test_*.sh`. A unified runner would be useful.
2. **No VCR-style cassette recording** — network tests will need manual fixture updates if APIs change.
3. **No performance baselines** — tools like `data/table-query.py` on 100MB CSVs should be profiled.
4. **No fuzz testing** — malformed CSV, truncated JSON, corrupt PDFs aren't systematically tested.

Defer these until the first 5 packs stabilize.

---

## Summary

**Test hermetic tools for determinism and output shape. Test network tools for error handling and format. Use receipts as the source of truth for conformance. Lint early, test late.**
