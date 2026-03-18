#!/usr/bin/env python3
"""Tests for trust enforcement gate.

Key invariants:
- Clean reject triggers enforcement (exit 1)
- not_evaluated never triggers enforcement
- Load errors never trigger enforcement
- accept/warn never trigger enforcement
- Advisory is the default — enforcement is opt-in
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from importlib import import_module

enforce_mod = import_module("check-trust-enforcement")
check_enforcement = enforce_mod.check_enforcement


def _record(pack_name="pack_a", auth_status="authorized", decision="accept",
            auth_reasons=None, acc_reasons=None, load_errors=None):
    trust = {
        "authorization": {"status": auth_status, "reason_codes": auth_reasons or []},
        "acceptance": {"decision": decision, "target": "ci_gate", "reason_codes": acc_reasons or []},
    }
    if load_errors:
        trust["load_errors"] = load_errors
    return {"pack_name": pack_name, "trust": trust}


class TestEnforcementTriggering:
    def test_clean_reject_triggers(self):
        """Authorized signer + reject → enforcement triggered."""
        records = [_record(decision="reject", acc_reasons=["UNKNOWN_SIGNER"])]
        fail, reason = check_enforcement(json.dumps(records))
        assert fail is True
        assert "rejected" in reason
        assert "UNKNOWN_SIGNER" in reason

    def test_accept_does_not_trigger(self):
        records = [_record(decision="accept")]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False

    def test_warn_does_not_trigger(self):
        records = [_record(decision="warn", acc_reasons=["SIGNER_NOT_GRANTED"])]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False


class TestEnforcementSafety:
    def test_not_evaluated_auth_skipped(self):
        """not_evaluated authorization → no enforcement."""
        records = [_record(auth_status="not_evaluated", decision="reject")]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False

    def test_not_evaluated_acceptance_skipped(self):
        """not_evaluated acceptance → no enforcement."""
        records = [_record(decision="not_evaluated")]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False

    def test_load_errors_skipped(self):
        """Load errors present → no enforcement even if reject."""
        records = [_record(decision="reject", load_errors=["signers.yaml: broken"])]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False

    def test_empty_records_passes(self):
        fail, _ = check_enforcement(json.dumps([]))
        assert fail is False

    def test_invalid_json_passes(self):
        fail, _ = check_enforcement("not json")
        assert fail is False

    def test_revoked_signer_reject_enforced(self):
        """Revoked signer with clean reject → enforcement triggered."""
        records = [_record(auth_status="revoked", decision="reject",
                           acc_reasons=["SIGNER_REVOKED"])]
        fail, reason = check_enforcement(json.dumps(records))
        assert fail is True
        assert "SIGNER_REVOKED" in reason


class TestMultiPack:
    def test_one_reject_among_accepts_triggers(self):
        """If any pack is rejected, enforcement triggers."""
        records = [
            _record(pack_name="good", decision="accept"),
            _record(pack_name="bad", decision="reject", acc_reasons=["POLICY_VIOLATION"]),
        ]
        fail, reason = check_enforcement(json.dumps(records))
        assert fail is True
        assert "bad" in reason

    def test_all_accept_passes(self):
        records = [
            _record(pack_name="a", decision="accept"),
            _record(pack_name="b", decision="accept"),
        ]
        fail, _ = check_enforcement(json.dumps(records))
        assert fail is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
