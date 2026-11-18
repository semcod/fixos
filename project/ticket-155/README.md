# Ticket 155: Pin POA, MCP, NL-URI, and SSOT governance contracts for Wellman check

- **ID**: ticket-155
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#168` / `PLF-21819` governance slice).

## Goal and scope

1. Pin exact 40-hex revisions and `sha256:` contract digests for `wellmanifest/poa`
   (`0.1.0@b0432f3729e6da51cf0c7007970cb16bb971f937`), `wellmanifest/mcp`
   (`0.1.0@91f02710715ad46818bf84e21c34dde390a89653`), `wellmanifest/nl-uri-dsl-llm`
   (`1.5.0@adc005677d835f46c540a760c9a89f29ba4a96ee`), and `wellmanifest/uriprocess`
   (`0.3.0@0a81334ce0d04a3adac26070597c95ceb44c42c4`) in `.governance/standards-lock.json`.
2. Add `.governance/poa.json` (acyclic 4-step FixOS POA DAG),
   `.governance/nl-uri-profile.json` (`semantic-v1` + `wellmanifest.nl-plan/v1`),
   `.governance/dsl-manifest.json`, and `.governance/llm.json` (secret-free MCP
   profile), and bind `.governance/poa.json` SHA-256 in `.governance/standard-adoption.json`.
3. Preserve `.governance/manifest.lock.json` byte-for-byte and respect the `#174`
   (`refs/heads/ticket/110-sync-standard-requirements-backup`) scope fence on
   `.governance/standard-requirements.json`.

## Acceptance criteria

- [x] AC-01: `python3 .governance/standard_pack_check.py --root .` passes (`findings=0`).
- [x] AC-02: `wellman check --root .` and explicit `-s` checks for `poa`, `mcp`,
      `nl-uri-dsl-llm`, `ssot`, `uriprocess`, `dsl`, and `llm` pass with 0 errors.
- [x] AC-03: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
