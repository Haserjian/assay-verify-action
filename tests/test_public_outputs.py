from pathlib import Path


ACTION_YML = Path(__file__).resolve().parents[1] / "action.yml"
EXAMPLE_GATE = Path(__file__).resolve().parents[1] / "examples" / "verify-pr-gate.yml"


def test_public_verdict_outputs_are_declared_and_written():
    text = ACTION_YML.read_text(encoding="utf-8")

    declared = {
        "pack-root-sha256",
        "integrity-verdict",
        "claim-verdict",
        "replay-verdict",
        "public-replay-verdict",
        "trust-verdict",
        "overall-verdict",
        "verify-report-json",
    }
    for name in declared:
        assert f"  {name}:" in text

    written = {
        "pack_root_sha256",
        "integrity_verdict",
        "claim_verdict",
        "replay_verdict",
        "public_replay_verdict",
        "trust_verdict",
        "overall_verdict",
        "verify_report_json",
    }
    for name in written:
        assert name in text


def test_verify_report_row_keeps_separate_verdict_channels():
    text = ACTION_YML.read_text(encoding="utf-8")

    assert '"integrity_verdict": sys.argv[4]' in text
    assert '"claim_verdict": sys.argv[5]' in text
    assert '"replay_verdict": sys.argv[6]' in text
    assert '"trust_verdict": sys.argv[7]' in text
    assert '"overall_verdict": sys.argv[8]' in text


def test_public_replay_verdict_is_distinct_from_legacy_replay_output():
    text = ACTION_YML.read_text(encoding="utf-8")

    assert "echo \"replay_verdict=${_VERDICT}\"" in text
    assert "echo \"public_replay_verdict=${_PUBLIC_REPLAY_VERDICT}\"" in text
    assert "PUBLIC_REPLAY_VERDICT_ALL=\"NOT_RUN\"" in text


def test_pr_gate_example_writes_explicit_report_artifact():
    example = EXAMPLE_GATE.read_text(encoding="utf-8")

    assert "--out verify_report.json" in example
    assert 'assay-version: "1.23.0"' not in example
    assert "assay.verify_report.v0.1" in example
    assert "verify_report.stdout.json" in example
    assert "cosign sign-blob" in example
    assert "--bundle verify_report.sigstore.json" in example
    assert "proof_pack_*/pack_manifest.json" in example


def test_action_does_not_introduce_receipt_json_noun():
    text = ACTION_YML.read_text(encoding="utf-8")
    assert "receipt.json" not in text
