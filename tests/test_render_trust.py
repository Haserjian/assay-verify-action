#!/usr/bin/env python3
"""Tests for trust summary rendering.

Covers: single pack, multi-pack, not_evaluated, load errors,
empty input, legacy fallback, backward compatibility.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from importlib import import_module

# Import the renderer module
render_mod = import_module("render-trust-summary")
render_trust_summary = render_mod.render_trust_summary


def test_single_pack_trust_present():
    """Trust block from single verify-pack JSON renders correctly."""
    data = {
        "trust": {
            "authorization": {"status": "authorized", "reason_codes": []},
            "acceptance": {"decision": "accept", "target": "ci_gate", "reason_codes": []},
        }
    }
    result = render_trust_summary(json.dumps(data))
    assert "### Trust Evaluation" in result
    assert "authorized" in result
    assert "accept" in result
    assert "ci_gate" in result


def test_multi_pack_renders_per_pack():
    """Multiple pack records render separate sections."""
    records = [
        {"pack_name": "pack_a", "trust": {
            "authorization": {"status": "authorized", "reason_codes": []},
            "acceptance": {"decision": "accept", "target": "ci_gate", "reason_codes": []},
        }},
        {"pack_name": "pack_b", "trust": {
            "authorization": {"status": "unrecognized", "reason_codes": ["SIGNER_NOT_IN_REGISTRY"]},
            "acceptance": {"decision": "reject", "target": "ci_gate", "reason_codes": ["UNKNOWN_SIGNER"]},
        }},
    ]
    result = render_trust_summary(json.dumps(records))
    assert "### Trust: `pack_a`" in result
    assert "### Trust: `pack_b`" in result
    assert "authorized" in result
    assert "unrecognized" in result
    assert "SIGNER_NOT_IN_REGISTRY" in result


def test_not_evaluated_renders_explicitly():
    """not_evaluated status must appear in output, not be omitted."""
    data = {
        "trust": {
            "authorization": {"status": "not_evaluated", "reason_codes": ["NO_REGISTRY"]},
            "acceptance": {"decision": "not_evaluated", "target": "ci_gate", "reason_codes": ["NO_POLICY"]},
        }
    }
    result = render_trust_summary(json.dumps(data))
    assert "not_evaluated" in result
    assert "NO_REGISTRY" in result
    assert "NO_POLICY" in result


def test_load_errors_rendered():
    """Trust load errors appear in output."""
    data = {
        "trust": {
            "authorization": {"status": "not_evaluated", "reason_codes": []},
            "acceptance": {"decision": "not_evaluated", "target": "ci_gate", "reason_codes": []},
            "load_errors": ["signers.yaml: invalid format"],
        }
    }
    result = render_trust_summary(json.dumps(data))
    assert "Trust policy load errors" in result
    assert "signers.yaml: invalid format" in result


def test_no_trust_block_produces_empty():
    """JSON without trust block produces empty output."""
    result = render_trust_summary(json.dumps({"status": "ok"}))
    assert result == ""


def test_empty_list_produces_empty():
    """Empty list of records produces empty output."""
    result = render_trust_summary(json.dumps([]))
    assert result == ""


def test_invalid_json_produces_empty():
    """Malformed JSON produces empty output, not crash."""
    result = render_trust_summary("not json at all")
    assert result == ""


def test_legacy_fallback_reason_code():
    """AUTHZ.LEGACY_ID_FALLBACK_USED appears when present in reason codes."""
    data = {
        "trust": {
            "authorization": {
                "status": "authorized",
                "reason_codes": ["AUTHZ.LEGACY_ID_FALLBACK_USED"],
            },
            "acceptance": {"decision": "accept", "target": "local_verify", "reason_codes": []},
        }
    }
    result = render_trust_summary(json.dumps(data))
    assert "AUTHZ.LEGACY_ID_FALLBACK_USED" in result


def test_advisory_note_always_present():
    """Advisory-only disclaimer must be in every non-empty output."""
    data = {
        "trust": {
            "authorization": {"status": "authorized", "reason_codes": []},
            "acceptance": {"decision": "accept", "target": "ci_gate", "reason_codes": []},
        }
    }
    result = render_trust_summary(json.dumps(data))
    assert "advisory only" in result


def test_output_is_deterministic():
    """Same input produces same output."""
    data = json.dumps({
        "trust": {
            "authorization": {"status": "authorized", "reason_codes": []},
            "acceptance": {"decision": "accept", "target": "ci_gate", "reason_codes": []},
        }
    })
    r1 = render_trust_summary(data)
    r2 = render_trust_summary(data)
    assert r1 == r2


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
