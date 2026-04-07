# Assay Verify Action

Verify AI evidence bundles in CI and surface the result directly on pull requests.

Use this action when your workflow already produces Assay proof packs and you want GitHub to verify them automatically. It checks pack integrity and behavioral claims, then posts the verdict where reviewers see it.

## What it looks like

On every PR, you get a comment like:

### Assay Verification

> [!WARNING]
> SHADOW MODE -- not enforced. At least one pack was produced in shadow mode.

**Result: SHADOW MODE -- not enforced**

| Pack | Integrity | Claims | Receipts | Mode |
|------|-----------|--------|----------|------|
| `proof_pack_abc123` | PASS | PASS | 12 | shadow (not enforced) |

> Exit code: `0` (`0` = all pass, `1` = claim fail, `2` = integrity fail)

## Quick start

The action assumes your workflow has already generated one or more proof packs.

```yaml
# .github/workflows/assay.yml
name: Assay
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: pip install assay-ai

      - name: Run with receipts
        run: assay run -c receipt_completeness -c guardian_enforcement -- python my_agent.py

      - name: Verify
        uses: Haserjian/assay-verify-action@v1
        with:
          pack-path: 'proof_pack_*/'
          require-claim-pass: 'true'
```

## RCE Replay Mode

RCE replay verification is available through `verification-mode: rce_replay`.

The contract for replay mode lives in [RCE_REPLAY_ACTION_CONTRACT.md](./RCE_REPLAY_ACTION_CONTRACT.md). It defines the replay-mode inputs, artifact layout expectations, verdict mapping, summary behavior, and explicit non-goals for PR E.

The determinism boundary for replay verdicts lives in [RCE_REPLAY_DETERMINISM_CONTRACT.md](./RCE_REPLAY_DETERMINISM_CONTRACT.md). That note defines what is pinned, what variation is admissible, and when `MATCH`, `DIVERGE`, or `INTEGRITY_FAIL` is the correct classification.

Replay mode still keeps the proof-pack path as the default. Use `verification-mode: rce_replay` only for replayable episode roots that already contain the layout expected by `assay rce-verify`.

### Replay mode outcome guide

Replay mode is intentionally narrow. It skips only when replay is explicitly optional and no replay roots are present; otherwise it fails closed.

| Replay roots matched | `require-pack` | `assay rce-verify` available | Outcome | Exit code | Notes |
|----------------------|----------------|------------------------------|---------|-----------|-------|
| no | `false` | not checked | success | `0` | Summary is `SKIPPED`. Replay mode does not require verifier availability when there is nothing to verify. |
| no | `true` | not checked | failure | `2` | No replay roots matched the configured `pack-path`. |
| yes | any | no | failure | `2` | Fail closed: replay was requested and roots exist, but verifier capability is missing. |
| yes | any | yes | success or failure | `0`, `1`, or `2` | Replay proceeds and maps `MATCH`, `DIVERGE`, and `INTEGRITY_FAIL` onto the normal action exit semantics. |

Once at least one replay root is found, missing replay surfaces, JSON parse failures, or verifier failures are integrity failures, not skip conditions.

### Machine-readable replay outputs

Replay mode now also emits stable machine-readable outputs so downstream policy or orchestration layers do not have to scrape markdown summaries.

| Output | Meaning |
|--------|---------|
| `replay-state` | `not_requested`, `skipped_no_roots`, `zero_roots_required`, `configuration_rejected`, `verifier_unavailable`, or `completed` |
| `replay-verdict` | Aggregate replay verdict: `MATCH`, `DIVERGE`, `INTEGRITY_FAIL`, or `N/A` |
| `replay-roots-matched` | Number of directories matched during replay discovery |
| `replay-results-json` | Compact JSON array of per-root replay rows with `pack`, `verdict`, `integrity`, `claims`, `steps_replayed`, and `replay_basis` |

These outputs are always populated. In normal proof-pack mode the replay surface is explicitly inert: `replay-state=not_requested`, `replay-verdict=N/A`, `replay-roots-matched=0`, and `replay-results-json=[]`.

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `pack-path` | `proof_pack_*/` | Path to Proof Pack directory (glob supported) |
| `verification-mode` | `proof_pack` | Select `proof_pack` or `rce_replay` |
| `replay-output-dir` | `replay_results` | Relative directory created inside each replay root for replay sidecars |
| `require-pack` | `true` | Fail if PR has file changes but no Proof Pack (set `false` for docs-only repos) |
| `require-claim-pass` | `true` | Fail if any claim check is not PASS |
| `lock-file` | | Path to `assay.lock` for pinned verification semantics |
| `comment-on-pr` | `true` | Post a summary comment on the pull request |
| `upload-artifact` | `true` | Upload pack as a workflow artifact |
| `trust-target` | | Trust evaluation target (`local_verify`, `ci_gate`, `publication`). Advisory unless `enforce-trust` is set. |
| `trust-policy-dir` | | Directory containing `signers.yaml` and `acceptance.yaml` |
| `enforce-trust` | `false` | When `true`, fail the step if trust acceptance is `reject` for the given target. Requires clean policy load. |
| `assay-version` | latest | Specific `assay-ai` version to install |
| `python-version` | `3.11` | Python version to use |

## Trust evaluation

The action can evaluate trust policy alongside verification. Trust is
**advisory by default** and does not affect exit codes unless you opt in.

### Advisory mode (default)

```yaml
- uses: Haserjian/assay-verify-action@v1
  with:
    pack-path: 'proof_pack_*/'
    trust-target: 'ci_gate'
    trust-policy-dir: 'trust/'
```

Shows trust authorization and acceptance status in the summary.
Does not affect pass/fail.

### Enforced mode

```yaml
- uses: Haserjian/assay-verify-action@v1
  with:
    pack-path: 'proof_pack_*/'
    trust-target: 'ci_gate'
    trust-policy-dir: 'trust/'
    enforce-trust: 'true'
```

Fails the step (exit 1) if any pack is **cleanly rejected** for the target.

Enforcement rules:
- Only triggers when acceptance is explicitly `reject`
- Never triggers when trust is `not_evaluated` (no policy loaded)
- Never triggers when policy has load errors (broken config stays advisory)
- Never triggers on `warn` or `accept`

If multiple packs are verified, any single clean reject for the enforced
target fails the step.

This means: broken config does not block your pipeline. Only a deliberate
policy rejection causes enforcement failure.

## Artifact uploads

When `upload-artifact` is enabled (the default), proof packs are uploaded as
GitHub workflow artifacts. These are **operational outputs for review and
debugging** — not receipt-backed trust artifacts.

Artifact visibility and retention follow GitHub's artifact settings, not Assay
trust semantics. Do not treat artifact presence, naming, or retention as proof
identity or signed lineage. If you are working in a public repo or a
mixed-sensitivity environment, consider setting `upload-artifact: false` and
managing evidence artifacts through a controlled channel instead.

## Outputs

| Output | Description |
|--------|-------------|
| `integrity` | `PASS` or `FAIL` |
| `claims` | `PASS`, `FAIL`, or `N/A` |
| `exit-code` | `0` (all pass), `1` (claim fail), `2` (integrity fail) |
| `pack-count` | Number of packs verified |
| `replay-state` | Machine-readable replay execution state |
| `replay-verdict` | Aggregate replay verdict or `N/A` |
| `replay-roots-matched` | Number of replay roots matched during discovery |
| `replay-results-json` | Compact JSON array of per-root replay results |
| `summary` | Markdown summary of results |

## Exit code contract

| Code | Meaning | Is this a bug? |
|------|---------|----------------|
| **0** | Integrity PASS and claims PASS | No. Everything checks out. |
| **1** | Integrity PASS, claims FAIL | **No.** The evidence is genuine, but the system didn't meet behavioral requirements. This is an honest failure report. |
| **2** | Integrity FAIL | **Yes.** Evidence is tampered, corrupted, or structurally invalid. Investigate. |

Exit 1 is not a failure of the tool. It means the AI system produced genuine evidence that it didn't do what was claimed. That's Assay working correctly.

## Lock-enforced verification

Pin your verification contract so every environment uses the same claim set:

```yaml
      - name: Verify with lock
        uses: Haserjian/assay-verify-action@v1
        with:
          pack-path: 'proof_pack_*/'
          lock-file: 'assay.lock'
```

Generate the lockfile:

```bash
assay lock write --cards receipt_completeness,guardian_enforcement -o assay.lock
```

## What Assay proves (and doesn't)

**Proves:**
- Evidence hasn't been tampered with after creation
- Specific behavioral claims pass or fail against the evidence
- Results are deterministic and reproducible

**Does not prove:**
- Evidence was honestly created in the first place
- The AI system is "safe" in any universal sense
- Timestamps are from a trusted source

Assay is a flight recorder, not a safety certificate.

## Related Repos

| Repo | Role |
|------|------|
| [assay](https://github.com/Haserjian/assay) | Core CLI + SDK (canonical source) |
| [assay-verify-action](https://github.com/Haserjian/assay-verify-action) | GitHub Action for CI verification (this repo) |
| [assay-ledger](https://github.com/Haserjian/assay-ledger) | Public transparency ledger |
| [assay-proof-gallery](https://github.com/Haserjian/assay-proof-gallery) | Live demo packs (PASS / HONEST FAIL / TAMPERED) |

## Links

- [assay-ai on PyPI](https://pypi.org/project/assay-ai/)
- [Quickstart docs](https://github.com/Haserjian/assay/blob/main/docs/README_quickstart.md)
- [Assay source](https://github.com/Haserjian/assay)
