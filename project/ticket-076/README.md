# Ticket 076: register reuse and nohardcode in wellman requirements; fixos nohardcode policy

- **ID**: ticket-076
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

- `wellman adopt auto --standard wellmanifest/reuse --standard
  wellmanifest/nohardcode` (wellman 0.20.38) adds both to
  `.governance/standard-requirements.json`.
- `.governance/nohardcode-policy.json` starts from nohardcode 922cc51's
  policy. Deviations: engines fixos does not use are disabled (YOLO, OCR,
  phonetic, ranking, DAG planner, hardware probe); NOHARDCODE-007 is a
  warning because `print()` in interactive CLI modules is terminal output,
  not operational logging; tests, docs, docker scenarios and governance
  files are excluded.

Audit with this policy on the base revision: 186 findings, 3 errors —
2× NOHARDCODE-006 (fixed by ticket-074 / #103) and 1× NOHARDCODE-009 in the
demo `main()` of `cleanup_planner.py` (left for a lint ticket: that file has
47 pre-existing ruff findings). Upstream policy: 195 findings, 148 errors.

ssot, semver and uriprocess are unknown to wellman 0.20.38 and to the managed
`standard-packs.json` catalog; their pins are in
`docs/INFORMATION/WELLMANIFEST_STANDARDS.md` (ticket-075).

SESSION_EXECUTION_AUTHORIZATION: user requested implementing wellmanifest wellman, nohardcode and reuse in fixos.

## Acceptance criteria

- [x] AC-01: `wellman check` passes and the nohardcode checker loads the repository policy.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
