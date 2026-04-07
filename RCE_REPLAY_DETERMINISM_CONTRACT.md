# RCE Replay Determinism Contract

Status: draft for issue #7. This note is contract-first on purpose.

This document defines the replay determinism boundary for `verification-mode: rce_replay`.

The existing [RCE Replay Action Contract](./RCE_REPLAY_ACTION_CONTRACT.md) defines the action surface: inputs, outputs, artifact discovery, and summary behavior. This note defines the colder boundary behind those outputs:

- what a replay root must pin
- what may vary across environments
- what counts as admissible drift
- when `MATCH`, `DIVERGE`, and `INTEGRITY_FAIL` are constitutionally correct

## Purpose

- Make replay verdicts governable instead of merely functional.
- Separate replay-root truth from runner noise.
- Prevent accidental promotion of under-specified or environment-sensitive roots into trusted `MATCH` results.
- Define the fixture matrix that must exist before replay determinism claims widen further.

## Non-goals

This note does not introduce:

- `live_reexecution`
- hybrid verification routing
- trust-policy evaluation in replay mode
- lock-file enforcement in replay mode
- implementation changes to `assay rce-verify`

It is a contract-definition artifact first. Implementation should follow the contract, not the other way around.

## Terms

- Replay root: a matched directory verified in `rce_replay` mode.
- Hash-bearing surface: any file or declared field whose value participates in proof identity or replay comparison.
- Byte-stable: exact bytes must remain unchanged for the surface to remain trustworthy.
- Semantically stable: insignificant serialization differences are allowed if the canonical value is unchanged.
- Admissible environment: a runner context that stays within the replay contract and does not introduce undeclared causal inputs.

## 1. Replay Root Invariants

### 1.1 Required surfaces

Every replay root must contain these paths:

| Path | Role | Contract status |
|------|------|-----------------|
| `pack_manifest.json` | proof-pack manifest / attestation surface | required |
| `receipt_pack.jsonl` | canonical receipt lineage surface | required |
| `episode_contract.json` | replay objective, script, policy, and environment contract | required |
| `inputs/` | bound replay inputs referenced by the episode contract | required |
| `recorded_traces/` | recorded trace artifacts keyed by replay step | required |

Missing required paths are not drift. They are `INTEGRITY_FAIL`.

### 1.2 Canonical path rules

- Paths in `episode_contract.json` are replay-root relative. They must not depend on absolute host paths.
- Each `inputs[].ref` must resolve under `inputs/` exactly once.
- Recorded traces for replayed steps must resolve under `recorded_traces/<step_id>.json` or another explicitly declared contract path once such a contract exists.
- Post-verification sidecars such as `replay_results/rce_replay_result.json` are outside the root integrity boundary. They are outputs of verification, not inputs to truth.

### 1.3 Hash-bearing surfaces

The current repo evidence already binds these surfaces:

| Surface | Current evidence | Stability class | Contract |
|---------|------------------|-----------------|----------|
| `receipt_pack.jsonl` | replay builder emits chained receipts with canonical receipt hashes | byte-stable transport, semantically stable receipt payloads | receipt order, lineage, and receipt content must remain trustworthy; corruption or truncation is `INTEGRITY_FAIL` |
| `pack_manifest.json` | proof-pack build output | byte-stable | manifest mutation after pack creation is `INTEGRITY_FAIL` |
| `episode_contract.json` | builder derives `episode_spec_hash` from `inputs`, `replay_script`, `replay_policy`, and environment subset | semantically stable for canonical JSON content | whitespace or key-order churn alone must not create `DIVERGE`; changed semantic content is a different replay root |
| `inputs/*` | builder hashes raw `input.json` bytes into `inputs[].hash` | byte-stable | if bytes change, integrity is broken |
| `recorded_traces/*.json` | builder compares structured JSON traces by hashed replay outputs | semantically stable for canonical JSON value | canonicalization-only JSON churn belongs in `MATCH`, not `DIVERGE` |

### 1.4 Byte-stable vs semantically stable

Use the stricter rule unless a surface is explicitly declared semantically stable.

- Byte-stable surfaces must survive transport unchanged.
- Semantically stable JSON surfaces may vary in formatting or object-key order only if the verifier's canonical form is unchanged.
- If a surface is not explicitly admitted as semantically stable, treat changes as integrity-relevant.

## 2. Environment Admissibility

Replay verification does not require the producer's original machine. It does require an admissible environment.

### 2.1 Admissible variation

The following runner-level differences may vary without changing replay truth, provided the replay root does not bind them as causal inputs:

- temporary directories
- workspace checkout paths
- process IDs
- wall-clock time at verification
- unrelated environment variables
- host OS details that do not change declared replay semantics

These variations are operational noise, not replay inputs.

### 2.2 Bound environment surfaces

The replay contract currently binds environment meaning through `episode_contract.json`, including:

- `environment.provider`
- `environment.model_id`
- `environment.tool_versions`
- `environment.container_digest`

If replay correctness depends on another environment surface, that surface must be declared and bound. Hidden dependencies are not tolerated.

### 2.3 Interpreter and tool version tolerance

- Patch-level verifier-runtime variation is admissible only when it does not alter replay semantics.
- If replay behavior depends on exact interpreter or library versions, that dependency must be captured under `tool_versions` or `container_digest`.
- Major or minor tool-version drift that changes replay semantics is not honest `DIVERGE`; it is an inadmissible environment and therefore `INTEGRITY_FAIL` unless the contract explicitly allows it.

### 2.4 Network stance

Recorded-trace replay is an offline truth surface by default.

- Replay must not require live network access to determine verdicts.
- If a replay root requires live external state to interpret comparison results, the root is under-specified.
- Under-specified roots are `INTEGRITY_FAIL`, not `DIVERGE`.

### 2.5 Randomness and seeds

- Uncaptured randomness is not admissible.
- If randomness affects replayed outputs, the seed or equivalent causal input must be bound into the replay root.
- A root that depends on randomness without binding that dependency is structurally untrustworthy and must produce `INTEGRITY_FAIL`.

## 3. Verdict Semantics

### 3.1 MATCH

`MATCH` means all of the following are true:

- the replay root is structurally complete
- hash-bearing surfaces pass integrity checks
- the verifier is operating in an admissible environment
- replayed outputs are equivalent under the contract's admitted equivalence rules

`MATCH` does not mean the original episode was universally correct. It means the current replay held under the declared contract.

### 3.2 DIVERGE

`DIVERGE` is an honest replay difference with intact integrity.

Use `DIVERGE` only when:

- the replay root is trustworthy enough to compare
- the environment is admissible
- the verifier can execute comparison normally
- one or more replayed outputs differ semantically from the recorded truth surface

`DIVERGE` is evidence about behavior, not evidence of tampering.

### 3.3 INTEGRITY_FAIL

`INTEGRITY_FAIL` means the verifier cannot treat the replay result as trustworthy comparison evidence.

This includes:

- missing or malformed required replay surfaces
- corrupted or tampered hash-bearing artifacts
- JSON parse failure or untrustworthy verifier output surface
- undeclared environment dependency
- inadmissible environment drift
- uncaptured randomness or other missing causal inputs

If the verifier cannot trust the comparison basis, the result must be `INTEGRITY_FAIL`, not `DIVERGE`.

### 3.4 Classification rule

Use this ladder in order:

1. Can the verifier trust the replay root and comparison basis? If no: `INTEGRITY_FAIL`.
2. Can the verifier execute replay under an admissible environment? If no: `INTEGRITY_FAIL`.
3. If trust and admissibility hold, are the compared outputs equivalent? If yes: `MATCH`.
4. If trust and admissibility hold but outputs differ: `DIVERGE`.

## 4. Fixture Matrix

Issue #7 should land a fixture matrix before wider replay claims are made.

| Fixture family | Current repo status | Expected verdict | What it proves |
|----------------|---------------------|------------------|----------------|
| clean match | present (`build-rce-test-pack.py match`) | `MATCH` | baseline replay equivalence |
| expected divergence | present (`build-rce-test-pack.py diverge`) | `DIVERGE` | honest behavioral drift with intact integrity |
| malformed replay root | missing | `INTEGRITY_FAIL` | required-surface failures are not treated as drift |
| environment drift | missing | `INTEGRITY_FAIL` unless explicitly admitted | undeclared or out-of-bound environment differences fail closed |
| canonicalization edge case | missing | `MATCH` | semantic JSON equivalence survives formatting or key-order churn |

### 4.1 Required fixture behaviors

- Malformed root fixture: remove or corrupt one required replay surface such as `episode_contract.json` or `recorded_traces/`.
- Environment drift fixture: create a case where replay depends on a changed environment surface that is not admitted by the contract.
- Canonicalization fixture: preserve JSON meaning while changing serialization form, proving the verifier does not mistake formatting churn for divergence.

### 4.2 Promotion gate

Do not widen replay claims, hybrid routing, or policy dependence until this fixture matrix exists and passes in CI.

## 5. Implementation Gate For Issue #7

Issue #7 is complete only when all of the following are true:

- this determinism contract is adopted as the governing note for replay verdict interpretation
- the missing fixture families are implemented
- CI proves the contract on the fixture matrix
- README and replay action docs link to this note as the determinism authority

Until then, replay mode is functional and legible, but its determinism boundary remains only partially proven.