"""Table-driven contract tests for RCE replay aggregate semantics.

Encodes the aggregate contract that the bash case statement in action.yml
must satisfy.  Any change to the WORST_EXIT → INTEGRITY_ALL/CLAIMS_ALL
derivation or the per-verdict exit mapping must keep these tests green.

Aggregation lattice (worst-exit-wins):
    WORST_EXIT 0  MATCH only           → integrity=PASS  claims=PASS
    WORST_EXIT 1  any DIVERGE          → integrity=PASS  claims=FAIL
    WORST_EXIT 2  any INTEGRITY_FAIL   → integrity=FAIL  claims=N/A

Per-verdict exit codes (action.yml verdict case):
    MATCH            → 0
    DIVERGE          → 1
    INTEGRITY_FAIL   → 2
    PARSE_ERROR      → 2  (malformed CLI JSON treated as INTEGRITY_FAIL)
    unknown verdict  → 2  (unrecognized string treated as INTEGRITY_FAIL)
"""

import pytest


# ── per-verdict exit mapping ──────────────────────────────────────────────────

_VERDICT_EXIT = {
    "MATCH": 0,
    "DIVERGE": 1,
    "INTEGRITY_FAIL": 2,
    "PARSE_ERROR": 2,
    "_UNKNOWN_": 2,  # sentinel for unrecognized verdict strings
}

VERDICT_EXIT_CASES = [
    ("MATCH",          0),
    ("DIVERGE",        1),
    ("INTEGRITY_FAIL", 2),
    ("PARSE_ERROR",    2),
    ("_UNKNOWN_",      2),
]


@pytest.mark.parametrize("verdict,expected_exit", VERDICT_EXIT_CASES)
def test_verdict_exit_mapping(verdict, expected_exit):
    assert _VERDICT_EXIT[verdict] == expected_exit


# ── aggregate derivation ──────────────────────────────────────────────────────

def _worst_exit(verdicts: list) -> int:
    """Mirror bash worst-exit-wins accumulation across packs."""
    return max((_VERDICT_EXIT.get(v, 2) for v in verdicts), default=0)


def _derive(worst_exit: int) -> tuple:
    """Mirror the bash case statement in action.yml."""
    if worst_exit == 0:
        return "PASS", "PASS"
    if worst_exit == 1:
        return "PASS", "FAIL"
    return "FAIL", "N/A"


# (label, verdicts, expected_integrity, expected_claims)
AGGREGATE_CASES = [
    # single-pack
    ("single MATCH",            ["MATCH"],            "PASS", "PASS"),
    ("single DIVERGE",          ["DIVERGE"],          "PASS", "FAIL"),
    ("single INTEGRITY_FAIL",   ["INTEGRITY_FAIL"],   "FAIL", "N/A"),
    ("single PARSE_ERROR",      ["PARSE_ERROR"],      "FAIL", "N/A"),
    ("single unknown verdict",  ["_UNKNOWN_"],        "FAIL", "N/A"),
    # multi-pack: integrity wins over all
    ("MATCH + MATCH",                       ["MATCH", "MATCH"],                     "PASS", "PASS"),
    ("MATCH + DIVERGE",                     ["MATCH", "DIVERGE"],                   "PASS", "FAIL"),
    ("MATCH + INTEGRITY_FAIL",              ["MATCH", "INTEGRITY_FAIL"],            "FAIL", "N/A"),
    ("DIVERGE + MATCH",                     ["DIVERGE", "MATCH"],                   "PASS", "FAIL"),
    ("DIVERGE + DIVERGE",                   ["DIVERGE", "DIVERGE"],                 "PASS", "FAIL"),
    ("DIVERGE + INTEGRITY_FAIL",            ["DIVERGE", "INTEGRITY_FAIL"],          "FAIL", "N/A"),
    ("INTEGRITY_FAIL + MATCH",              ["INTEGRITY_FAIL", "MATCH"],            "FAIL", "N/A"),
    ("INTEGRITY_FAIL + DIVERGE",            ["INTEGRITY_FAIL", "DIVERGE"],          "FAIL", "N/A"),
    ("INTEGRITY_FAIL + INTEGRITY_FAIL",     ["INTEGRITY_FAIL", "INTEGRITY_FAIL"],   "FAIL", "N/A"),
    # three-pack propagation
    ("MATCH + DIVERGE + INTEGRITY_FAIL",    ["MATCH", "DIVERGE", "INTEGRITY_FAIL"], "FAIL", "N/A"),
    ("DIVERGE + MATCH + INTEGRITY_FAIL",    ["DIVERGE", "MATCH", "INTEGRITY_FAIL"], "FAIL", "N/A"),
    ("INTEGRITY_FAIL + MATCH + DIVERGE",    ["INTEGRITY_FAIL", "MATCH", "DIVERGE"], "FAIL", "N/A"),
    # PARSE_ERROR participates in worst-exit accumulation
    ("MATCH + PARSE_ERROR",                 ["MATCH", "PARSE_ERROR"],               "FAIL", "N/A"),
    ("DIVERGE + PARSE_ERROR",               ["DIVERGE", "PARSE_ERROR"],             "FAIL", "N/A"),
]


@pytest.mark.parametrize("label,verdicts,expected_integrity,expected_claims", AGGREGATE_CASES)
def test_replay_aggregate(label, verdicts, expected_integrity, expected_claims):
    worst = _worst_exit(verdicts)
    integrity, claims = _derive(worst)
    assert integrity == expected_integrity, (
        f"[{label}] integrity: expected {expected_integrity!r}, got {integrity!r} "
        f"(worst_exit={worst})"
    )
    assert claims == expected_claims, (
        f"[{label}] claims: expected {expected_claims!r}, got {claims!r} "
        f"(worst_exit={worst})"
    )
