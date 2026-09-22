#!/bin/bash
# tests/test_registry_lookup.py — test net/registry-lookup.py with package registries

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing net/registry-lookup.py..."

# Test 1: PyPI lookup (real package, latest version)
echo "  [1/5] PyPI: requests (latest)"
$FRAGLETC registry-lookup.py \
  -p registry=pypi \
  -p package=requests \
  -p version=latest \
  -p format=markdown \
  --receipt $OUTPUT/pypi_requests.json

EXIT_CODE=$(jq -r '.exit_code' $OUTPUT/pypi_requests.json)
test "$EXIT_CODE" = "0" || (echo "FAIL: PyPI lookup failed (exit $EXIT_CODE)"; exit 1)
grep -q "requests\|version" $OUTPUT/pypi_requests.json || (echo "FAIL: PyPI response missing"; exit 1)
echo "    ✓ PyPI lookup OK"

# Test 2: PyPI JSON format
echo "  [2/5] PyPI: JSON format"
$FRAGLETC registry-lookup.py \
  -p registry=pypi \
  -p package=requests \
  -p format=json \
  --receipt $OUTPUT/pypi_json.json
grep -q '"name"\|"version"' $OUTPUT/pypi_json.json || (echo "FAIL: JSON format"; exit 1)
echo "    ✓ PyPI JSON OK"

# Test 3: npm package
echo "  [3/5] npm: express"
$FRAGLETC registry-lookup.py \
  -p registry=npm \
  -p package=express \
  -p version=latest \
  -p format=markdown \
  --receipt $OUTPUT/npm_express.json

EXIT_CODE=$(jq -r '.exit_code' $OUTPUT/npm_express.json)
test "$EXIT_CODE" = "0" || (echo "FAIL: npm lookup failed (exit $EXIT_CODE)"; exit 1)
echo "    ✓ npm lookup OK"

# Test 4: crates.io
echo "  [4/5] crates.io: tokio"
$FRAGLETC registry-lookup.py \
  -p registry=crates \
  -p package=tokio \
  -p version=latest \
  -p format=markdown \
  --receipt $OUTPUT/crates_tokio.json

EXIT_CODE=$(jq -r '.exit_code' $OUTPUT/crates_tokio.json)
test "$EXIT_CODE" = "0" || (echo "FAIL: crates lookup failed (exit $EXIT_CODE)"; exit 1)
echo "    ✓ crates.io OK"

# Test 5: Docker Hub
echo "  [5/5] Docker Hub: library/alpine"
$FRAGLETC registry-lookup.py \
  -p registry=dockerhub \
  -p 'package=library/alpine' \
  -p version=latest \
  -p format=markdown \
  --receipt $OUTPUT/docker_alpine.json

EXIT_CODE=$(jq -r '.exit_code' $OUTPUT/docker_alpine.json)
test "$EXIT_CODE" = "0" || (echo "FAIL: Docker Hub lookup failed (exit $EXIT_CODE)"; exit 1)
echo "    ✓ Docker Hub OK"

echo "✓ All net/registry-lookup.py tests passed"
