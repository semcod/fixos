# Ticket 080: reviewed nohardcode waiver for the OLLAMA_HOST default

- **ID**: ticket-080
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

After tickets 074 and 078 the only blocking wellmanifest/nohardcode finding in
fixos is NOHARDCODE-006 on `DEFAULT_OLLAMA_HOST`, the fallback used when
`OLLAMA_HOST` is unset or empty. Inlining it into `getenv` would change the
empty-value behaviour covered by `test_ollama_endpoint.py`, and rewriting it
only to dodge the line scanner would hide rather than review it.

The line carries the reviewed inline waiver introduced by
wellmanifest/nohardcode#6 (`# nohardcode: allow NOHARDCODE-006 -- reason`).
With that checker: 0 blocking errors; the finding stays visible as waived.

SESSION_EXECUTION_AUTHORIZATION: user selected "DEFAULT_OLLAMA_HOST" from the remaining tasks.

## Acceptance criteria

- [x] AC-01: nohardcode checker (with #6) reports 0 errors and 1 waived finding for fixos.
- [x] AC-02: Ollama endpoint tests and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
