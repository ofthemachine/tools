#!/bin/bash
# tests/test_pdf_to_images.sh — test doc/pdf-to-images.py

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
FIXTURES=$(pwd)/tests/fixtures
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing doc/pdf-to-images.py..."

# Test 1: single page to PNG
echo "  [1/4] single page to PNG"
$FRAGLETC pdf-to-images.py \
  -p "pdf_source=$FIXTURES/sample.pdf" \
  -p page=1 \
  -p scale=2.0 \
  --output page.png \
  --receipt $OUTPUT/page1.json

test -f $OUTPUT/page.png || (echo "FAIL: no output PNG"; exit 1)
file $OUTPUT/page.png | grep -q PNG || (echo "FAIL: not valid PNG"; exit 1)
MEMO1=$(jq -r '.memo_key' $OUTPUT/page1.json)
test -n "$MEMO1" || (echo "FAIL: no memo_key"; exit 1)
echo "    ✓ single page OK"

# Test 2: all pages to tar.gz bundle
echo "  [2/4] all pages to tar.gz"
$FRAGLETC pdf-to-images.py \
  -p "pdf_source=$FIXTURES/sample.pdf" \
  -p page=all \
  -p scale=2.0 \
  --output pages.tar.gz \
  --receipt $OUTPUT/all_pages.json

test -f $OUTPUT/pages.tar.gz || (echo "FAIL: no tar.gz"; exit 1)
tar -tzf $OUTPUT/pages.tar.gz | grep -q "page-" || (echo "FAIL: no page images in tar"; exit 1)
echo "    ✓ all pages to tar.gz OK"

# Test 3: different scale factors (determinism)
echo "  [3/4] scale factor variations"
for scale in 1.0 2.0 3.0; do
  $FRAGLETC pdf-to-images.py \
    -p "pdf_source=$FIXTURES/sample.pdf" \
    -p page=1 \
    -p "scale=$scale" \
    --receipt $OUTPUT/scale_${scale}.json
  test -f $OUTPUT/scale_${scale}.json || (echo "FAIL: scale $scale failed"; exit 1)
done
echo "    ✓ scale factors OK"

# Test 4: determinism — same input, same memo_key
echo "  [4/4] determinism check"
$FRAGLETC pdf-to-images.py \
  -p "pdf_source=$FIXTURES/sample.pdf" \
  -p page=1 \
  -p scale=2.0 \
  --receipt $OUTPUT/page1b.json
MEMO2=$(jq -r '.memo_key' $OUTPUT/page1b.json)
test "$MEMO1" = "$MEMO2" || (echo "FAIL: non-deterministic"; exit 1)
echo "    ✓ determinism OK"

echo "✓ All doc/pdf-to-images.py tests passed"
