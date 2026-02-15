# Repo Charter: assay-verify-action

## Purpose

Composite GitHub Action that verifies Assay Proof Packs in CI. Posts
verification results as PR comments and uploads packs as artifacts.

## Trust Boundary

**Public.** This action runs in customer CI environments. It installs
`assay-ai` from PyPI and calls `assay verify-pack`. No secrets are
embedded; the action itself is stateless.

## What Lives Here

- `action.yml` -- composite action definition
- Action scripts (shell-based, no compiled dependencies)
- Documentation for CI integration patterns

## What Does Not Live Here

- The Assay CLI or SDK (consumed from PyPI)
- Ledger submission logic (see `assay-ledger`)
- Receipt generation or signing (happens in the core repo)

## Versioning Contract

- Tagged releases: `v1`, `v1.x.y`
- `v1` is a floating major tag (always points to latest `v1.x.y`)
- Breaking changes require a new major version (`v2`)
- The action's `assay-version` input controls which `assay-ai` version is installed
- Exit codes follow Assay's contract: `0/1/2`

## Consumer Workflow

```yaml
# .github/workflows/assay.yml
- name: Verify
  uses: Haserjian/assay-verify-action@v1
  with:
    pack-path: 'proof_pack_*/'
    require-claim-pass: 'true'
    lock-file: 'assay.lock'  # optional: pin verification contract
```

## Related Repos

| Repo | Role |
|------|------|
| [assay](https://github.com/Haserjian/assay) | Core CLI + SDK (canonical source) |
| [assay-ledger](https://github.com/Haserjian/assay-ledger) | Public transparency ledger |
