#!/bin/bash
# tests/test_plot.sh — test chart/plot.py with various inputs

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
FIXTURES=$(pwd)/tests/fixtures
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing chart/plot.py..."

# Test 1: bar chart from CSV file
echo "  [1/6] bar chart from CSV file"
$FRAGLETC plot.py \
  -p "data=$FIXTURES/sales.csv" \
  -p type=bar \
  -p x=month \
  -p y=revenue \
  --output result.svg \
  --receipt $OUTPUT/bar.json

test -f $OUTPUT/result.svg || (echo "FAIL: no output file"; exit 1)
grep -q '<svg' $OUTPUT/result.svg || (echo "FAIL: not valid SVG"; exit 1)
grep -q 'month\|January' $OUTPUT/result.svg || (echo "FAIL: missing data in chart"; exit 1)
MEMO1=$(jq -r '.memo_key' $OUTPUT/bar.json)
test -n "$MEMO1" || (echo "FAIL: no memo_key (not conformant)"; exit 1)
echo "    ✓ bar chart OK (memo_key: ${MEMO1:0:16}...)"

# Test 2: line chart from CSV
echo "  [2/6] line chart from CSV file"
$FRAGLETC plot.py \
  -p "data=$FIXTURES/products.csv" \
  -p type=line \
  -p x=product \
  -p y=q1 \
  --output result.svg \
  --receipt $OUTPUT/line.json
grep -q '<svg' $OUTPUT/result.svg || (echo "FAIL: line chart not valid SVG"; exit 1)
echo "    ✓ line chart OK"

# Test 3: pie chart
echo "  [3/6] pie chart from CSV"
$FRAGLETC plot.py \
  -p "data=$FIXTURES/products.csv" \
  -p type=pie \
  -p x=product \
  -p y=q1 \
  --output result.svg \
  --receipt $OUTPUT/pie.json
grep -q '<svg' $OUTPUT/result.svg || (echo "FAIL: pie chart not valid SVG"; exit 1)
echo "    ✓ pie chart OK"

# Test 4: scatter chart
echo "  [4/6] scatter chart from CSV"
$FRAGLETC plot.py \
  -p "data=$FIXTURES/products.csv" \
  -p type=scatter \
  -p x=q1 \
  -p y=q4 \
  --output result.svg \
  --receipt $OUTPUT/scatter.json
grep -q '<svg' $OUTPUT/result.svg || (echo "FAIL: scatter chart not valid SVG"; exit 1)
echo "    ✓ scatter chart OK"

# Test 5: determinism — same input, same memo_key
echo "  [5/6] determinism check"
$FRAGLETC plot.py \
  -p "data=$FIXTURES/sales.csv" \
  -p type=bar \
  -p x=month \
  -p y=revenue \
  --receipt $OUTPUT/bar2.json
MEMO2=$(jq -r '.memo_key' $OUTPUT/bar2.json)
test "$MEMO1" = "$MEMO2" || (echo "FAIL: non-deterministic (memo_keys differ: $MEMO1 vs $MEMO2)"; exit 1)
echo "    ✓ determinism OK"

# Test 6: error handling — invalid chart type
echo "  [6/6] error handling (invalid chart type)"
if $FRAGLETC plot.py \
  -p "data=$FIXTURES/sales.csv" \
  -p type=invalid \
  -p x=month \
  -p y=revenue \
  --receipt $OUTPUT/err.json 2>&1 | grep -q "unsupported chart type"; then
  EXIT_CODE=$(jq -r '.exit_code' $OUTPUT/err.json)
  test "$EXIT_CODE" != "0" || (echo "FAIL: should have non-zero exit code"; exit 1)
  echo "    ✓ error handling OK (exit code $EXIT_CODE)"
else
  echo "FAIL: error handling not working as expected"
  exit 1
fi

echo "✓ All chart/plot.py tests passed"
