# Ticket 079: ssot decision: diagnostic command tables flagged by redup are allowed divergence

- **ID**: ticket-079
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

redup 0.4.48 (min 10 lines, 0.80 similarity) reports two clone groups:
`_find_downloads_cleanup` / `_diagnose_snap` / `_diagnose_lvm` and
`_diagnose_swap_optimization` / `_diagnose_filesystem_health`. Each returns
`{name: _cmd(probe)}` with different shell probes; the only shared logic is
the existing `_cmd` helper. `python3 -m ssot interview` classifies them as
`allowed_divergence` → `document_known_divergent`, forbidding
`treat_analyzer_as_debt`. The decision is recorded in `docs/ssot/`, and
`WELLMANIFEST_STANDARDS.md` (version 3) reflects it, the reuse fixes
(reuse#10, #12) and the open gap (reuse#13). Stray backslash escapes in that
page are removed.

SESSION_EXECUTION_AUTHORIZATION: user requested continuing, merging, standardizing and testing.

## Acceptance criteria

- [x] AC-01: `ssot validate` accepts the decision; docs checker has no findings on the page.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
