# RCE Replay Action Contract

Status: design gate for PR E. This branch implements the contract in assay-verify-action.

This note defines the user-facing contract for adding Replay-Constrained Episode (RCE) verification to this action without widening scope beyond the current recorded-trace verifier in Haserjian/assay PR B and the gallery scenarios in Haserjian/assay-proof-gallery PR C.

## Purpose

- Keep the existing proof-pack verification path as the default and preserve backward compatibility.
- Make recorded-trace RCE verification runnable in GitHub Actions without re-implementing verifier logic in this repo.
- Preserve the existing Assay exit semantics: `0` pass, `1` honest fail, `2` integrity fail.
- Define the configuration boundary before any action code is added.

## Scope

PR E is intentionally narrow.

- Replay basis: `recorded_trace` only
- Comparator tier: `A` only
- Verifier implementation: `assay rce-verify`
- Artifact output: replay-result sidecars written next to the original replayable pack

PR E does not include:

- `live_reexecution`
- replay-bundle packing or non-null `dispute.replay_pack_root_sha256`
- TypeScript verification
- trust-policy evaluation in replay mode
- lock-file enforcement in replay mode

## Input Contract

PR E should add one new input and keep the existing proof-pack inputs stable.

| Input | Contract |
|------|----------|
| `verification-mode` | New enum input. Allowed values: `proof_pack` (default), `rce_replay`. |
| `pack-path` | Reused as-is. In replay mode, each matched directory is treated as a replayable episode root. |
| `replay-output-dir` | New input. Default: `replay_results`. Relative directory created inside each matched replay root. |
| `require-pack` | Reused as-is. No matched directories follows the current skip/fail behavior. |
| `comment-on-pr` | Reused as-is. Replay mode still writes a sticky PR comment when enabled. |
| `upload-artifact` | Reused as-is. Replay sidecars live under the matched roots, so the existing upload step can carry them. |
| `assay-version` | Reused as-is. Replay mode requires an `assay-ai` version that includes `assay rce-verify`. |
| `python-version` | Reused as-is. |

The following existing inputs should be rejected as configuration errors in replay mode v1:

| Input | Reason |
|------|--------|
| `require-claim-pass: false` | `assay rce-verify` already encodes `DIVERGE` as exit `1`. Replay mode must not create a soft-pass path for honest divergence. |
| `lock-file` | No replay-specific lock contract is defined yet. |
| `trust-target` | Replay mode v1 does not evaluate trust policy. |
| `trust-policy-dir` | Replay mode v1 does not evaluate trust policy. |
| `enforce-trust` | Replay mode v1 does not evaluate trust policy. |

Why `verification-mode` instead of `replay-mode: true`:

- It scales better than boolean feature flags.
- It makes the default proof-pack path explicit.
- It avoids implying that replay mode is just a switch on top of `verify-pack`.

## Artifact Discovery Rules

Replay mode should follow the current action's pack discovery behavior and then apply stricter replay-layout checks.

1. Expand `pack-path` the same way the current action does.
2. Ignore non-directory matches.
3. If no directories match:
   - `require-pack: false` -> preserve the current `SKIPPED` behavior
   - `require-pack: true` -> preserve the current exit `2` behavior
4. If directories match, each matched replay root must contain the layout expected by `assay rce-verify`:
   - `pack_manifest.json`
   - `receipt_pack.jsonl`
   - `episode_contract.json`
   - `inputs/`
   - `recorded_traces/`
5. Missing or malformed replay surfaces are not skip conditions. They are `INTEGRITY_FAIL` for that target.

The action should invoke replay verification as:

```bash
assay rce-verify <pack_dir> \
  --out-dir <pack_dir>/<replay-output-dir> \
  --overwrite \
  --json
```

## Runtime Contract

Replay mode must remain a thin wrapper around the canonical CLI.

- The action continues to install `assay-ai` from PyPI.
- After installation, replay mode must probe for `assay rce-verify` and fail closed with a clear error if the command is unavailable.
- The action must parse the CLI's JSON output instead of scraping human-readable text.
- JSON parse failure is treated as exit `2` because the action can no longer trust the verifier result surface.

PR E should document a minimum `assay-ai` version once the replay-enabled release is tagged. Until then, the contract is semantic: replay mode requires the first release that contains PR B.

## Verdict Mapping

Replay mode keeps the existing action-level exit model and maps it onto RCE verdicts directly.

| RCE verdict | Action `integrity` | Action `claims` | Exit code | GitHub step outcome |
|------------|--------------------|-----------------|-----------|---------------------|
| `MATCH` | `PASS` | `PASS` | `0` | success |
| `DIVERGE` | `PASS` | `FAIL` | `1` | failure |
| `INTEGRITY_FAIL` | `FAIL` | `N/A` | `2` | failure |

For multi-pack runs, the worst exit code wins, matching the current proof-pack action behavior.

`claim_check: null` in the replay receipt maps to the action output `claims=N/A`.

## Output Contract

PR E should preserve the existing outputs instead of inventing a parallel replay-only output surface.

| Output | Replay mode mapping |
|--------|---------------------|
| `integrity` | `PASS` or `FAIL` from the worst replay result |
| `claims` | `PASS`, `FAIL`, or `N/A` from the worst replay result |
| `exit-code` | `0`, `1`, or `2` |
| `pack-count` | Number of replay roots evaluated |
| `summary` | Markdown summary for step summary and sticky PR comment |

No new required outputs are needed for PR E.

## Summary And Comment Contract

Replay mode should reuse the current sticky comment mechanism and step-summary flow.

- Keep the existing sticky comment marker.
- Keep writing the same `summary` output and `GITHUB_STEP_SUMMARY` content.
- Add an explicit mode line near the top of the summary, for example:

```markdown
### Assay Verification

**Mode: RCE replay (`recorded_trace`, Tier A)**
```

- In replay mode, the per-target table should expose replay-relevant facts instead of proof-pack claim-card columns.

Recommended replay-mode table:

| Pack | Verdict | Integrity | Claims | Steps Replayed | Replay Basis |
|------|---------|-----------|--------|----------------|--------------|

PR E does not require GitHub annotations. The step summary, sticky comment, and uploaded artifacts are the intended operator surfaces.

## Artifact Upload Contract

Replay results should be written inside each matched replay root under `<replay-output-dir>/` so the current upload-artifact step can keep using `pack-path`.

Expected replay sidecars:

- `rce_replay_result.json`
- `rce_replay_details.json`

The action does not mint a new replay bundle in PR E. It uploads the original replayable roots plus the sidecars produced during CI.

## Deferred Items

These remain intentionally outside PR E:

- replay-bundle packing and non-null `replay_pack_root_sha256`
- public promotion of the hidden `rce-verify` CLI
- CRS naming reconciliation
- trust-policy evaluation for replay mode
- TypeScript parity

## Implementation Gate

PR E is ready to start only if the implementation follows this contract exactly:

- one mode selector, not ad hoc replay booleans
- fail closed on unsupported inputs and missing replay surfaces
- CLI wrapper only, no verifier reimplementation in the action
- preserve the existing action outputs and sticky comment flow
- keep replay mode limited to recorded-trace v0