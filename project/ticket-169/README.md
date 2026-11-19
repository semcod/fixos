# ticket-169: ci(workflows): add native macOS and Windows integration test matrix

- **ID**: ticket-169
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Extend the `test` matrix job in `.github/workflows/ci.yml` with native `macos-latest` and `windows-latest` matrix legs (Python `3.12`, LF checkout fidelity) that run the cross-platform quick-scan, cache-classification, CLI, anonymizer, rollback, and MCP/POA integration suites natively on macOS and Windows runners while preserving the canonical `test` job identifier in `.governance/required-checks.json`.

## Acceptance criteria

- [x] AC-01: `.github/workflows/ci.yml` runs `jobs.test` across `ubuntu-latest` (`3.10`, `3.11`, `3.12`) plus native `macos-latest` (`3.12`) and `windows-latest` (`3.12`), satisfying `.governance/required-checks.json` (`GOV-SYNC-001` pass).
- [x] AC-02: `./project/governance-check.sh` passes with zero errors and zero warnings.
