#!/bin/bash
# tests/test_inspect_convert.sh — test sheet/inspect.py and sheet/convert.py

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
FIXTURES=$(pwd)/tests/fixtures
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing sheet/inspect.py and sheet/convert.py..."

# Test inspect.py: metadata extraction
echo "  [1/6] sheet/inspect.py metadata extraction"
$FRAGLETC inspect.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p format=markdown \
  --receipt $OUTPUT/inspect.json

test -f $OUTPUT/inspect.json || (echo "FAIL: no receipt"; exit 1)
grep -q "Sheet1\|Sheet2" $OUTPUT/inspect.json || (echo "FAIL: no sheet names in output"; exit 1)
MEMO1=$(jq -r '.memo_key' $OUTPUT/inspect.json)
test -n "$MEMO1" || (echo "FAIL: no memo_key"; exit 1)
echo "    ✓ inspect.py OK"

# Test inspect.py: JSON format
echo "  [2/6] sheet/inspect.py JSON format"
$FRAGLETC inspect.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p format=json \
  --receipt $OUTPUT/inspect_json.json
grep -q '"sheets"\|"rows"' $OUTPUT/inspect_json.json || (echo "FAIL: JSON format check"; exit 1)
echo "    ✓ inspect.py JSON OK"

# Test convert.py: extract sheet to CSV
echo "  [3/6] sheet/convert.py to CSV"
$FRAGLETC convert.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p sheet=1 \
  -p format=csv \
  --output data.csv \
  --receipt $OUTPUT/convert_csv.json

test -f $OUTPUT/data.csv || (echo "FAIL: no CSV output"; exit 1)
head -1 $OUTPUT/data.csv | grep -q "," || (echo "FAIL: CSV format check"; exit 1)
echo "    ✓ convert.py to CSV OK"

# Test convert.py: extract sheet to JSON
echo "  [4/6] sheet/convert.py to JSON"
$FRAGLETC convert.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p sheet=1 \
  -p format=json \
  --output data.json \
  --receipt $OUTPUT/convert_json.json

test -f $OUTPUT/data.json || (echo "FAIL: no JSON output"; exit 1)
grep -q '\[{"\|]' $OUTPUT/data.json || (echo "FAIL: JSON format check"; exit 1)
MEMO2=$(jq -r '.memo_key' $OUTPUT/convert_json.json)
test -n "$MEMO2" || (echo "FAIL: no memo_key"; exit 1)
echo "    ✓ convert.py to JSON OK"

# Test convert.py: by sheet name (if available)
echo "  [5/6] sheet/convert.py by sheet name"
$FRAGLETC convert.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p sheet=Sheet1 \
  -p format=csv \
  --output by_name.csv \
  --receipt $OUTPUT/by_name.json
echo "    ✓ convert.py by sheet name OK"

# Test determinism
echo "  [6/6] determinism check"
$FRAGLETC convert.py \
  -p "spreadsheet=$FIXTURES/sample.xlsx" \
  -p sheet=1 \
  -p format=json \
  --receipt $OUTPUT/convert_json2.json
MEMO3=$(jq -r '.memo_key' $OUTPUT/convert_json2.json)
test "$MEMO2" = "$MEMO3" || (echo "FAIL: non-deterministic"; exit 1)
echo "    ✓ determinism OK"

echo "✓ All sheet tests passed"
