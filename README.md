# Assay Verify Action

Verify AI evidence bundles (Proof Packs) in CI. Posts results as a PR comment.

A Proof Pack is a signed, tamper-evident folder that proves what an AI system did during a run. This action verifies pack integrity and behavioral claims, then surfaces the verdict where reviewers see it.

## What it looks like

On every PR, you get a comment like:

### Assay Verification

**Result: PASS**

| Pack | Integrity | Claims | Receipts | Mode |
|------|-----------|--------|----------|------|
| `proof_pack_abc123` | PASS | PASS | 12 | shadow |

> Exit code: `0` (`0` = all pass, `1` = claim fail, `2` = integrity fail)

## Quick start

```yaml
# .github/workflows/assay.yml
name: Assay
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
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

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `pack-path` | `proof_pack_*/` | Path to Proof Pack directory (glob supported) |
| `require-claim-pass` | `true` | Fail if any claim check is not PASS |
| `lock-file` | | Path to `assay.lock` for pinned verification semantics |
| `comment-on-pr` | `true` | Post a summary comment on the pull request |
| `upload-artifact` | `true` | Upload pack as a workflow artifact |
| `assay-version` | latest | Specific `assay-ai` version to install |
| `python-version` | `3.11` | Python version to use |

## Outputs

| Output | Description |
|--------|-------------|
| `integrity` | `PASS` or `FAIL` |
| `claims` | `PASS`, `FAIL`, or `N/A` |
| `exit-code` | `0` (all pass), `1` (claim fail), `2` (integrity fail) |
| `pack-count` | Number of packs verified |
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

## Links

- [assay-ai on PyPI](https://pypi.org/project/assay-ai/)
- [Quickstart docs](https://github.com/Haserjian/assay/blob/main/docs/README_quickstart.md)
- [Assay source](https://github.com/Haserjian/assay)
