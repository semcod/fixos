# Ticket 145: Handle all IPP faults and execute printer repairs without a shell

- **ID**: ticket-145
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user asked to execute
  backlog tasks for `semcod/fixos` and verify proper operation (`PLF-21824` /
  GitHub issue `#183`, 2026-11-18).

## Goal and scope

Resolve `PLF-21824` / `semcod/fixos#183`:
1. Evaluate each comma-separated IPP `printer-state-reasons` token
   independently so mixed fault/report lists such as
   `media-empty-error,toner-low-report` are never suppressed when the trailing
   token ends with `-report`.
2. Replace `subprocess.run(finding.command, ..., shell=True)` in
   `fixos/cli/printers_cmd.py` with validated structured repair specifications
   and `shell=False` argument vectors in `fixos/plugins/builtin/printer_repairs.py`.

## Acceptance criteria

- [x] AC-01: `active_fault_reasons` and `Plugin.diagnose()` detect IPP faults
      regardless of token ordering, multiple faults, whitespace, and
      report-only lists.
- [x] AC-02: Printer repairs execute strictly via validated `argv` sequences
      with `shell=False`, rejecting hostile queue names and malformed IP
      addresses while preserving Linux, macOS, and Windows repair semantics.
- [x] AC-03: Governance check, Ruff, and Wellman check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
