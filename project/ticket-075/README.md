# Ticket 075: wellmanifest ssot decision, standards applicability and troubleshooting docs

- **ID**: ticket-075
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

Documentation part of adopting wellman, ssot, nohardcode, semver, uriprocess
and reuse in fixos:

- `docs/INFORMATION/WELLMANIFEST_STANDARDS.md`: per standard the pinned
  revision, how it applies and the evidence (semver: host package only;
  uriprocess: not applicable; nohardcode audit summary).
- `docs/ssot/`: interviews and decisions for `fixos.version` (VERSION
  canonical, pyproject parity-gated, setup.py reads VERSION) and
  `fixos.ollama-endpoint` (`ollama_host_url()`), produced by
  `python3 -m ssot interview` and accepted by `ssot validate` (91c894b).
- `docs/SERVICE/TROUBLESHOOTING.md`: runbook for wellmanifest/reuse REUSE-006.

Conflict found: REUSE-006B only accepts `docs/TROUBLESHOOTING.md` or
`errors/*.md`, while wellmanifest/docs requires profile documents under
`docs/<KIND>/`; the docs rule is followed.

SESSION_EXECUTION_AUTHORIZATION: user requested implementing wellmanifest ssot, nohardcode, semver, uriprocess and reuse in fixos.

## Acceptance criteria

- [x] AC-01: docs checker has no findings on the deliverables; both ssot decisions validate.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
