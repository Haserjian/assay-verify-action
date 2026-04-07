#!/usr/bin/env python3
"""Build a minimal RCE test pack for self-test CI jobs.

Usage:
    python build-rce-test-pack.py <scenario> <output_dir>

Scenarios:
    match           -- All recorded traces match receipt hashes (exit 0)
    diverge         -- Recorded traces differ from receipts (exit 1)
    tampered        -- Receipt tampered before replay (exit 2)
    malformed_root  -- Required replay surface removed after pack build (exit 2)
    environment_drift -- Bound environment field mutated after pack build (exit 2)
    canonicalization -- JSON formatting/key-order churn only (exit 0)

The output directory is created (or replaced) with a complete RCE episode root
that assay rce-verify accepts, including a real signed proof pack.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from assay._receipts.canonicalize import prepare_receipt_for_hashing
from assay._receipts.jcs import canonicalize as jcs_canonicalize
from assay.keystore import AssayKeyStore
from assay.proof_pack import ProofPack


SIGNER_ID = "self-test-signer"
SUPPORTED_SCENARIOS = (
    "match",
    "diverge",
    "tampered",
    "malformed_root",
    "environment_drift",
    "canonicalization",
)


def _sha256_prefixed(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _canonical_hash(payload) -> str:
    return _sha256_prefixed(jcs_canonicalize(payload))


def _receipt_hash(receipt: dict) -> str:
    return _sha256_prefixed(jcs_canonicalize(prepare_receipt_for_hashing(dict(receipt))))


def _episode_spec_hash(contract: dict) -> str:
    env = contract["environment"]
    return _canonical_hash({
        "inputs": contract["inputs"],
        "replay_script": contract["replay_script"],
        "replay_policy": contract["replay_policy"],
        "environment": {
            "provider": env["provider"],
            "model_id": env["model_id"],
            "tool_versions": env["tool_versions"],
            "container_digest": env["container_digest"],
        },
    })


def _make_receipt(*, receipt_id, receipt_type, seq, payload, parent_hashes,
                  timestamp="2026-04-06T12:00:00+00:00"):
    receipt = {
        "receipt_id": receipt_id,
        "type": receipt_type,
        "timestamp": timestamp,
        "schema_version": "3.0",
        "seq": seq,
        "proof_tier": "core",
        "parent_hashes": parent_hashes,
        **payload,
    }
    receipt["receipt_hash"] = _receipt_hash(receipt)
    return receipt


def _write_json(path: Path, payload: dict, *, indent: int | None = None) -> None:
    path.write_text(json.dumps(payload, indent=indent), encoding="utf-8")


def _build_pack(scenario: str, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)

    ks_dir = out_dir.parent / ".self_test_keys"
    ks = AssayKeyStore(ks_dir)
    if not ks.has_key(SIGNER_ID):
        ks.generate_key(SIGNER_ID)

    input_data = {"item": "self-test", "value": 42}
    transform_output = {"result": "ok", "score": 1.0}
    input_bytes = json.dumps(input_data, separators=(",", ":"), sort_keys=True).encode()
    input_hash = _sha256_prefixed(input_bytes)

    environment = {
        "provider": "synthetic",
        "model_id": "self-test-v0",
        "tool_versions": {"assay": "0.0.0"},
        "container_digest": None,
    }
    environment["env_fingerprint_hash"] = _canonical_hash(environment)
    environment["model_version_hint"] = None
    environment["system_fingerprint"] = None

    contract = {
        "schema_version": "rce/0.1",
        "episode_id": "ep_000000000000000000000001",
        "objective": "Self-test episode",
        "inputs": [{"ref": "input.json", "hash": input_hash, "media_type": "application/json"}],
        "replay_script": {
            "schema_version": "replay_script/0.1",
            "steps": [
                {"step_id": "s01", "opcode": "LOAD_INPUT", "params": {"ref": "input.json"}, "depends_on": []},
                {"step_id": "s02", "opcode": "APPLY_TRANSFORM", "params": {"transform": "score"}, "depends_on": ["s01"]},
                {"step_id": "s03", "opcode": "EMIT_OUTPUT", "params": {"claim_type": "score", "output_ref": "s02"}, "depends_on": ["s02"]},
            ],
        },
        "replay_policy": {"replay_basis": "recorded_trace", "comparator_tier": "A"},
        "environment": environment,
    }

    # Canonical traces for receipts
    traces = {"s01": input_data, "s02": transform_output, "s03": transform_output}

    spec_hash = _episode_spec_hash(contract)
    episode_id = contract["episode_id"]
    env = contract["environment"]

    s01_hash = _canonical_hash(traces["s01"])
    s02_hash = _canonical_hash(traces["s02"])
    s03_hash = _canonical_hash(traces["s03"])
    inputs_hash = _canonical_hash(contract["inputs"])
    script_hash = _canonical_hash(contract["replay_script"])
    outputs_hash = _canonical_hash([{"step_id": "s03", "output_hash": s03_hash}])

    open_r = _make_receipt(
        receipt_id="r_open_001", receipt_type="rce.episode_open/v0", seq=0,
        parent_hashes=[],
        payload={
            "episode_id": episode_id, "episode_spec_hash": spec_hash,
            "objective": contract["objective"],
            "inputs_hash": inputs_hash, "script_hash": script_hash,
            "env_fingerprint_hash": env["env_fingerprint_hash"],
            "replay_basis": "recorded_trace", "comparator_tier": "A", "n_steps": 3,
        },
    )
    s1 = _make_receipt(
        receipt_id="r_step_001", receipt_type="rce.episode_step/v0", seq=1,
        parent_hashes=[open_r["receipt_hash"]],
        payload={
            "episode_id": episode_id, "step_id": "s01", "opcode": "LOAD_INPUT",
            "step_status": "PASS", "input_hashes": [], "output_hash": s01_hash,
            "output_size_bytes": 30, "duration_ms": 1, "comparator_tier": "A",
        },
    )
    s2 = _make_receipt(
        receipt_id="r_step_002", receipt_type="rce.episode_step/v0", seq=2,
        parent_hashes=[s1["receipt_hash"]],
        payload={
            "episode_id": episode_id, "step_id": "s02", "opcode": "APPLY_TRANSFORM",
            "step_status": "PASS", "input_hashes": [s01_hash], "output_hash": s02_hash,
            "output_size_bytes": 40, "duration_ms": 2, "comparator_tier": "A",
            "provider": "synthetic", "model_id": "self-test-v0",
        },
    )
    s3 = _make_receipt(
        receipt_id="r_step_003", receipt_type="rce.episode_step/v0", seq=3,
        parent_hashes=[s2["receipt_hash"]],
        payload={
            "episode_id": episode_id, "step_id": "s03", "opcode": "EMIT_OUTPUT",
            "step_status": "PASS", "input_hashes": [s02_hash], "output_hash": s03_hash,
            "output_size_bytes": 40, "duration_ms": 1, "comparator_tier": "A",
        },
    )
    close_r = _make_receipt(
        receipt_id="r_close_001", receipt_type="rce.episode_close/v0", seq=4,
        parent_hashes=[s3["receipt_hash"]],
        payload={
            "episode_id": episode_id, "episode_spec_hash": spec_hash,
            "outputs_hash": outputs_hash,
            "n_steps_executed": 3, "n_steps_passed": 3, "all_steps_passed": True,
            "replay_basis": "recorded_trace", "comparator_tier": "A",
        },
    )

    receipts = [open_r, s1, s2, s3, close_r]

    # Tampered scenario: corrupt inputs_hash in open receipt (breaks Phase 3)
    if scenario == "tampered":
        receipts[0]["inputs_hash"] = "sha256:" + ("bb" * 32)

    # Build real signed pack
    pack_dir = ProofPack(
        run_id="self_test_rce",
        entries=receipts,
        signer_id=SIGNER_ID,
    ).build(out_dir, keystore=ks)

    # Add episode artifacts
    _write_json(pack_dir / "episode_contract.json", contract, indent=2)
    (pack_dir / "inputs").mkdir(exist_ok=True)
    (pack_dir / "inputs" / "input.json").write_bytes(input_bytes)
    traces_dir = pack_dir / "recorded_traces"
    traces_dir.mkdir(exist_ok=True)

    # Diverge scenario: swap recorded traces for s02/s03 with different content
    if scenario == "diverge":
        alt_output = {"result": "ok", "score": 0.5}  # different from canonical
        traces["s02"] = alt_output
        traces["s03"] = alt_output

    for step_id, trace in traces.items():
        trace_path = traces_dir / f"{step_id}.json"
        if scenario == "canonicalization" and step_id in {"s02", "s03"}:
            reordered = {"score": trace["score"], "result": trace["result"]}
            _write_json(trace_path, reordered, indent=2)
            continue
        trace_path.write_text(json.dumps(trace), encoding="utf-8")

    if scenario == "environment_drift":
        contract["environment"]["tool_versions"]["assay"] = "9.9.9"
        _write_json(pack_dir / "episode_contract.json", contract, indent=2)

    if scenario == "malformed_root":
        (pack_dir / "episode_contract.json").unlink()

    print(f"Built {scenario} pack at {pack_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in SUPPORTED_SCENARIOS:
        print(
            "Usage: build-rce-test-pack.py "
            "<match|diverge|tampered|malformed_root|environment_drift|canonicalization> <output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)
    _build_pack(sys.argv[1], Path(sys.argv[2]))
