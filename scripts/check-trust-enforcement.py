#!/usr/bin/env python3
"""Check trust enforcement gate.

Reads trust records from stdin (JSON array) and determines whether
any pack has a clean reject that should fail the step.

Exit codes:
  0 = pass (no enforcement triggered)
  1 = enforcement triggered (at least one clean reject)

Enforcement is only triggered when:
  - acceptance.decision == "reject"
  - no load_errors present
  - authorization.status != "not_evaluated"

When trust is not_evaluated or has load errors, enforcement does NOT
trigger — those cases remain advisory to avoid failing on broken config.
"""
import json
import sys


def check_enforcement(json_str: str) -> tuple[bool, str]:
    """Check if any trust record triggers enforcement.

    Returns (should_fail, reason).
    """
    try:
        records = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return False, ""

    if not isinstance(records, list):
        return False, ""

    for record in records:
        trust = record.get("trust", {})
        pack_name = record.get("pack_name", "unknown")

        # Skip if load errors present — don't enforce broken config
        if trust.get("load_errors"):
            continue

        auth = trust.get("authorization", {})
        acc = trust.get("acceptance", {})

        # Skip if not evaluated
        if auth.get("status") == "not_evaluated":
            continue
        if acc.get("decision") == "not_evaluated":
            continue

        # Enforce: clean reject
        if acc.get("decision") == "reject":
            reason_codes = acc.get("reason_codes", [])
            reasons = ", ".join(reason_codes) if reason_codes else "no specific reason"
            return True, (
                f"Trust enforcement: pack '{pack_name}' rejected for "
                f"target '{acc.get('target', '?')}' "
                f"(authorization: {auth.get('status', '?')}, reasons: {reasons})"
            )

    return False, ""


if __name__ == "__main__":
    json_str = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not json_str:
        sys.exit(0)
    should_fail, reason = check_enforcement(json_str)
    if should_fail:
        print(reason, file=sys.stderr)
        sys.exit(1)
