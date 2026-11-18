# Ticket 149: Keep Fixos cleanup target JSON parseable

- **ID**: ticket-149
- **Owner**: agent:codex-forge-boundary
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested continued remediation of confirmed ecosystem autonomy failures.

The target-driven cleanup prints progress, nested tier output and recovery
hints to stdout before the final report. Autonomous callers cannot parse
the stream as one JSON document. Keep the existing cleanup effects and report
schema and send human-readable diagnostics to stderr in JSON mode.

## Acceptance criteria

- [x] AC-01: Both dry-run and execution return one JSON report on stdout.
- [x] AC-02: Cleanup diagnostics remain available and cleanup policy is preserved.
- [x] AC-03: Related cleanup and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

<!-- ticket-radar:start -->
## Ticket Radar

Assessment unavailable: managed ticket storage bridge declined the radar assessment.
Advisory only; no execution or merge approval.
<!-- ticket-radar:end -->
