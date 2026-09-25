#!/bin/bash
# tests/test_github.sh -- github/read-issue-form.py and github/check-approver.py against fixture events
set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
F=$(pwd)/tests/fixtures
fail() { echo "FAIL: $*"; exit 1; }

echo "Testing github/read-issue-form.py..."
out=$($FRAGLETC read-issue-form.py -p issue=$F/labeled-by-approver.json)
[ "$(echo "$out" | jq -r .fields.machine)" = Toaster ] || fail "machine field"
[ "$(echo "$out" | jq -r .fields.must_include)" = null ] || fail "_No response_ should be null"
[ "$(echo "$out" | jq -c .fields.agreements)" = '["This poem may be published"]' ] || fail "checkbox list"
[ "$(echo "$out" | jq -r .issue.number)" = 7 ] || fail "issue number"
out=$($FRAGLETC read-issue-form.py -p issue=$F/issue-body.md)
[ "$(echo "$out" | jq -r .fields.form)" = Haiku ] || fail "bare body"
[ "$(echo "$out" | jq -r '.issue|length')" = 0 ] || fail "bare body has no issue metadata"
echo "  ✓ read-issue-form OK"

echo "Testing github/check-approver.py..."
$FRAGLETC check-approver.py -p event=$F/labeled-by-approver.json -p approvers=$F/approvers -p label=poem:ready | grep -q "^approved: Frison labeled poem:ready on #7" || fail "approver (case-insensitive)"
if $FRAGLETC check-approver.py -p event=$F/labeled-by-outsider.json -p approvers=$F/approvers -p label=poem:ready; then fail "outsider was approved"; fi
if $FRAGLETC check-approver.py -p event=$F/labeled-other.json -p approvers=$F/approvers -p label=poem:ready; then fail "wrong label was approved"; fi
echo "  ✓ check-approver OK"
