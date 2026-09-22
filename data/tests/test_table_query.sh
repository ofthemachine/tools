#!/bin/bash
# tests/test_table_query.sh — test data/table-query.py with SQL queries

set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
FIXTURES=$(pwd)/tests/fixtures
OUTPUT=$(mktemp -d)
trap "rm -rf $OUTPUT" EXIT

echo "Testing data/table-query.py..."

# Test 1: GROUP BY aggregation
echo "  [1/5] GROUP BY aggregation"
$FRAGLETC table-query.py \
  -p "table_source=$FIXTURES/employees.csv" \
  -p 'query=SELECT dept, count(*) as count, round(avg(salary), 2) as avg_salary FROM data GROUP BY dept ORDER BY dept' \
  -p format=markdown \
  --receipt $OUTPUT/group_by.json

MEMO1=$(jq -r '.memo_key' $OUTPUT/group_by.json)
test -n "$MEMO1" || (echo "FAIL: no memo_key"; exit 1)
grep -q "Engineering\|Sales\|Marketing" $OUTPUT/group_by.json || (echo "FAIL: query result missing"; exit 1)
echo "    ✓ GROUP BY OK"

# Test 2: WHERE clause
echo "  [2/5] WHERE clause filtering"
$FRAGLETC table-query.py \
  -p "table_source=$FIXTURES/employees.csv" \
  -p 'query=SELECT name, salary FROM data WHERE salary > 80000 ORDER BY salary DESC' \
  -p format=markdown \
  --receipt $OUTPUT/where.json
test -f $OUTPUT/where.json || (echo "FAIL: no receipt"; exit 1)
echo "    ✓ WHERE clause OK"

# Test 3: JSON output format
echo "  [3/5] JSON output format"
$FRAGLETC table-query.py \
  -p "table_source=$FIXTURES/employees.csv" \
  -p 'query=SELECT name, dept FROM data LIMIT 3' \
  -p format=json \
  --receipt $OUTPUT/json_out.json
grep -q '"name"\|"dept"' $OUTPUT/json_out.json || (echo "FAIL: JSON output malformed"; exit 1)
echo "    ✓ JSON output OK"

# Test 4: CSV output format
echo "  [4/5] CSV output format"
$FRAGLETC table-query.py \
  -p "table_source=$FIXTURES/employees.csv" \
  -p 'query=SELECT name, salary FROM data LIMIT 2' \
  -p format=csv \
  --receipt $OUTPUT/csv_out.json
grep -q 'name,salary' $OUTPUT/csv_out.json || (echo "FAIL: CSV output malformed"; exit 1)
echo "    ✓ CSV output OK"

# Test 5: determinism
echo "  [5/5] determinism check"
$FRAGLETC table-query.py \
  -p "table_source=$FIXTURES/employees.csv" \
  -p 'query=SELECT dept, count(*) as count FROM data GROUP BY dept ORDER BY dept' \
  -p format=markdown \
  --receipt $OUTPUT/group_by2.json
MEMO2=$(jq -r '.memo_key' $OUTPUT/group_by2.json)
test "$MEMO1" = "$MEMO2" || (echo "FAIL: non-deterministic (memo_keys differ)"; exit 1)
echo "    ✓ determinism OK"

echo "✓ All data/table-query.py tests passed"
