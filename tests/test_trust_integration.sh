#!/usr/bin/env bash
# Integration tests for trust enforcement pipeline.
#
# Tests the full flow: accumulate-trust → render-trust-summary → check-trust-enforcement
# Proves enforcement behavior matches the documented contract.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="${SCRIPT_DIR}/../scripts"
PASS=0
FAIL=0

_assert_eq() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: $name"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $name (expected=$expected, actual=$actual)"
  fi
}

_assert_contains() {
  local name="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    PASS=$((PASS + 1))
    echo "  PASS: $name"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $name ('$needle' not found)"
  fi
}

# --- Helper: build a trust record ---
_trust_record() {
  local pack="$1" auth="$2" decision="$3" target="${4:-ci_gate}" reasons="${5:-}" load_errors="${6:-}"
  local rc_arr="[]"
  if [ -n "$reasons" ]; then
    rc_arr="[\"${reasons}\"]"
  fi
  local le=""
  if [ -n "$load_errors" ]; then
    le=",\"load_errors\":[\"${load_errors}\"]"
  fi
  echo "{\"pack_name\":\"${pack}\",\"trust\":{\"authorization\":{\"status\":\"${auth}\",\"reason_codes\":${rc_arr}},\"acceptance\":{\"decision\":\"${decision}\",\"target\":\"${target}\",\"reason_codes\":${rc_arr}}${le}}}"
}

# ============================================================
echo "=== Test 1: Advisory mode - accept does not fail ==="
RECORDS="[$(_trust_record pack_a authorized accept)]"
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
_assert_eq "accept exits 0" "0" "$?"

echo ""
echo "=== Test 2: Enforced mode - clean reject fails ==="
RECORDS="[$(_trust_record pack_a authorized reject ci_gate POLICY_REJECT)]"
set +e
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
RC=$?
set -e
_assert_eq "clean reject exits 1" "1" "$RC"

echo ""
echo "=== Test 3: not_evaluated does not fail ==="
RECORDS="[$(_trust_record pack_a not_evaluated not_evaluated ci_gate NO_POLICY)]"
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
_assert_eq "not_evaluated exits 0" "0" "$?"

echo ""
echo "=== Test 4: Load errors do not fail ==="
RECORDS='[{"pack_name":"pack_a","trust":{"authorization":{"status":"authorized","reason_codes":[]},"acceptance":{"decision":"reject","target":"ci_gate","reason_codes":["BROKEN"]},"load_errors":["signers.yaml: parse error"]}}]'
set +e
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
RC=$?
set -e
_assert_eq "load errors exits 0" "0" "$RC"

echo ""
echo "=== Test 5: Warn does not fail ==="
RECORDS="[$(_trust_record pack_a recognized warn ci_gate SIGNER_NOT_GRANTED)]"
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
_assert_eq "warn exits 0" "0" "$?"

echo ""
echo "=== Test 6: Multi-pack - any clean reject fails ==="
RECORDS="[$(_trust_record pack_good authorized accept), $(_trust_record pack_bad unrecognized reject ci_gate UNKNOWN_SIGNER)]"
set +e
echo "$RECORDS" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
RC=$?
set -e
_assert_eq "multi-pack any reject exits 1" "1" "$RC"

echo ""
echo "=== Test 7: Rendering pipeline produces output ==="
RECORDS="[$(_trust_record pack_a authorized accept)]"
RENDERED=$(echo "$RECORDS" | python3 "${SCRIPTS}/render-trust-summary.py")
_assert_contains "render produces markdown" "### Trust:" "$RENDERED"
_assert_contains "render shows authorization" "authorized" "$RENDERED"
_assert_contains "render shows advisory note" "advisory only" "$RENDERED"

echo ""
echo "=== Test 8: Accumulate pipeline works ==="
TMP=$(mktemp)
echo "[]" > "$TMP"
VERIFY_JSON='{"trust":{"authorization":{"status":"authorized","reason_codes":[]},"acceptance":{"decision":"accept","target":"ci_gate","reason_codes":[]}}}'
python3 "${SCRIPTS}/accumulate-trust.py" "$TMP" "$VERIFY_JSON" "pack_test" 2>/dev/null
COUNT=$(python3 -c "import json; print(len(json.load(open('$TMP'))))")
_assert_eq "accumulate adds record" "1" "$COUNT"
rm -f "$TMP"

echo ""
echo "=== Test 9: Full pipeline: accumulate → render → enforce ==="
TMP=$(mktemp)
echo "[]" > "$TMP"
REJECT_JSON='{"trust":{"authorization":{"status":"unrecognized","reason_codes":["SIGNER_NOT_IN_REGISTRY"]},"acceptance":{"decision":"reject","target":"ci_gate","reason_codes":["UNKNOWN_SIGNER"]}}}'
python3 "${SCRIPTS}/accumulate-trust.py" "$TMP" "$REJECT_JSON" "pack_rejected"
RENDERED=$(cat "$TMP" | python3 "${SCRIPTS}/render-trust-summary.py")
_assert_contains "full pipeline renders reject" "reject" "$RENDERED"
_assert_contains "full pipeline shows pack name" "pack_rejected" "$RENDERED"
set +e
cat "$TMP" | python3 "${SCRIPTS}/check-trust-enforcement.py" 2>/dev/null
RC=$?
set -e
_assert_eq "full pipeline enforces reject" "1" "$RC"
rm -f "$TMP"

echo ""
echo "=============================="
echo "Results: ${PASS} passed, ${FAIL} failed"
if [ $FAIL -gt 0 ]; then
  exit 1
fi
echo "ok: trust integration tests passed"
