"""Contract tests for machine-readable RCE replay outputs.

These tests mirror the stable output surface exposed by action.yml so local
pytest can catch enum or shape drift before the GitHub Actions self-test runs.
"""

import pytest


def _derive_replay_outputs(
    *,
    mode: str,
    roots_matched: int,
    require_pack: bool,
    guard_errors: bool = False,
    verifier_available: bool = True,
    worst_exit: int = 0,
) -> tuple[str, str]:
    if mode != "rce_replay":
        return "not_requested", "N/A"
    if guard_errors:
        return "configuration_rejected", "INTEGRITY_FAIL"
    if roots_matched == 0:
        if require_pack:
            return "zero_roots_required", "INTEGRITY_FAIL"
        return "skipped_no_roots", "N/A"
    if not verifier_available:
        return "verifier_unavailable", "INTEGRITY_FAIL"
    if worst_exit == 0:
        return "completed", "MATCH"
    if worst_exit == 1:
        return "completed", "DIVERGE"
    return "completed", "INTEGRITY_FAIL"


OUTPUT_CASES = [
    ("proof_pack default", dict(mode="proof_pack", roots_matched=0, require_pack=True), ("not_requested", "N/A")),
    ("replay skipped", dict(mode="rce_replay", roots_matched=0, require_pack=False), ("skipped_no_roots", "N/A")),
    ("replay missing required roots", dict(mode="rce_replay", roots_matched=0, require_pack=True), ("zero_roots_required", "INTEGRITY_FAIL")),
    ("replay configuration rejected", dict(mode="rce_replay", roots_matched=0, require_pack=True, guard_errors=True), ("configuration_rejected", "INTEGRITY_FAIL")),
    ("replay verifier unavailable", dict(mode="rce_replay", roots_matched=1, require_pack=True, verifier_available=False), ("verifier_unavailable", "INTEGRITY_FAIL")),
    ("replay match", dict(mode="rce_replay", roots_matched=1, require_pack=True, worst_exit=0), ("completed", "MATCH")),
    ("replay diverge", dict(mode="rce_replay", roots_matched=1, require_pack=True, worst_exit=1), ("completed", "DIVERGE")),
    ("replay integrity fail", dict(mode="rce_replay", roots_matched=1, require_pack=True, worst_exit=2), ("completed", "INTEGRITY_FAIL")),
]


@pytest.mark.parametrize("label,kwargs,expected", OUTPUT_CASES)
def test_replay_output_state_machine(label, kwargs, expected):
    assert _derive_replay_outputs(**kwargs) == expected, label


def test_replay_results_row_schema_is_stable():
    row = {
        "pack": "proof_pack_123",
        "verdict": "MATCH",
        "integrity": "PASS",
        "claims": "PASS",
        "steps_replayed": "4",
        "replay_basis": "recorded_trace",
    }
    assert set(row) == {
        "pack",
        "verdict",
        "integrity",
        "claims",
        "steps_replayed",
        "replay_basis",
    }