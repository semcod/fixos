# Ticket 146: Reject truncated LPD jobs in the printer twin sink

- **ID**: ticket-146
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user asked to execute
  backlog tasks for `semcod/fixos` and verify proper operation (`PLF-21825` /
  GitHub issue `#185`, 2026-11-18).

## Goal and scope

Resolve `PLF-21825` / `semcod/fixos#185` in `tests/twin/printers/job_sink.py`:
- Require `LpdHandler` to read the exact declared byte count plus a trailing
  `NUL` (`\x00`) terminator before acknowledging (`\x00`) or accumulating any
  control or data file.
- Ensure truncated, malformed, or un-terminated LPD transactions return NAK
  (`\x01`) and never create a completed spool file, while preserving any prior
  completed transactions.
- Add isolated ephemeral-loopback unit regressions in
  `tests/unit/test_printer_twin_sink.py`.

## Acceptance criteria

- [x] AC-01: `LpdHandler` rejects short data, missing/non-NUL terminators, and
      malformed subcommands without creating a spool file.
- [x] AC-02: Loopback unit tests cover raw binary, empty raw connection, valid
      binary LPD (ignoring client filename), multiple LPD data files,
      unsupported top-level command, truncated/un-terminated LPD jobs, and
      preservation of prior valid jobs.
- [x] AC-03: Governance check, Ruff, and Wellman check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
