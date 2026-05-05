import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "jurisdiction_receipts"
VALIDATOR = ROOT / "scripts" / "validate-jurisdiction-receipts.mjs"
ACTION_YML = ROOT / "action.yml"


VALID_RECEIPTS = [
    "valid-factorize.json",
    "valid-archive_hard.json",
    "valid-quarantine.json",
]

INVALID_RECEIPTS = [
    "invalid-routing-decision.json",
    "invalid-missing-candidate-elasticities.json",
    "invalid-extra-top-level-property.json",
    "invalid-selected-intervention-mismatch.json",
    "invalid-archive_hard-can-govern.json",
    "invalid-quarantine-can-govern.json",
    "invalid-factorize-without-child-receipts.json",
]


def _run_validator(*names: str) -> subprocess.CompletedProcess[str]:
    paths = [str(FIXTURES / name) for name in names]
    return subprocess.run(
        ["node", str(VALIDATOR), *paths],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_valid_jurisdiction_receipt_fixtures_pass():
    result = _run_validator(*VALID_RECEIPTS)

    assert result.returncode == 0, result.stderr
    for name in VALID_RECEIPTS:
        assert name in result.stdout


def test_invalid_jurisdiction_receipt_fixtures_fail():
    for name in INVALID_RECEIPTS:
        result = _run_validator(name)

        assert result.returncode == 2, name
        assert "Invalid Guardian jurisdiction receipt" in result.stderr
        assert name in result.stderr


def test_action_exposes_explicit_jurisdiction_receipt_input():
    action = ACTION_YML.read_text(encoding="utf-8")

    assert "jurisdiction-receipt-path:" in action
    assert "INPUT_JURISDICTION_RECEIPT_PATH" in action
    assert "validate-jurisdiction-receipts.mjs" in action


def test_action_keeps_jurisdiction_validation_explicit():
    action = ACTION_YML.read_text(encoding="utf-8")
    validation_index = action.index("Explicit Guardian jurisdiction receipt CI check")
    proof_pack_index = action.index("VERIFY_CMD=\"assay verify-pack $PACK_DIR\"")

    assert validation_index < proof_pack_index
    assert "if [ -n \"$INPUT_JURISDICTION_RECEIPT_PATH\" ]; then" in action
