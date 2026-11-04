# Ticket 130: Validate MCP inputs before adapter execution

- **ID**: ticket-130
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested "kontynuuj, scalaj, aktualizuj" after the POA/MCP audit. Implement PLF-21813 / GitHub issue162 and publish through the declared independent Validator. Allocation uses the adopted clone-local allocator, whose exact successful result reserved ticket-130. Use the managed v5 layout and exclusive initial lease for this newly allocated, session-owned ticket; preserve all pre-existing primary and quarantine work.

## Acceptance criteria

- [x] AC-01: URI, alias and MCP meta-tool arguments reject invalid types, nonfinite numbers, out-of-range age, unknown fields and missing required fields before adapters run.
- [x] AC-02: Valid calls preserve behavior; stable errors expose no submitted values. Negative tests spy on side-effect boundaries.
- [ ] AC-03: Affected and stack checks plus governance pass, then protected exact-head review and merge update Planfile and GitHub.

## Validation

MCP boundary suite: 118 passed. Full stack: 1201 passed, 5 existing skips, 16 default deselections, 2 environment warnings in 59.33s. Ruff and managed governance pass (0 errors/warnings). Publication preflight resolves the deployed protected profile and executor configuration; exact-head checks and independent review/merge remain pending. External recovery records retain command evidence.
