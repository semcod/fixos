# Ticket 077: clarify OLLAMA_BASE_URL as LLM-only override of the OLLAMA_HOST SSOT in docs

- **ID**: ticket-077
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

A Validator dry-run review of #104 (ticket-075) returned REQUEST_CHANGES: the
Ollama endpoint SSOT called `OLLAMA_HOST` the only endpoint while the runbook
said `OLLAMA_BASE_URL` overrides the LLM endpoint. The scheduled run approved
and merged the earlier head, so the inconsistency reached `main`; the
follow-up #106 was rejected by GOV-BASE-002 because ticket-075 was already
delivered.

This ticket states the layering in the ssot interview purpose (decision
regenerated with `python3 -m ssot interview`), `WELLMANIFEST_STANDARDS.md` and
`TROUBLESHOOTING.md` (both version 2).

SESSION_EXECUTION_AUTHORIZATION: user requested continuing, merging, standardizing and testing.

## Acceptance criteria

- [x] AC-01: docs checker has no findings on the deliverables; `ssot validate` accepts the decision.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
