# Ticket 178: Clean only the Cargo registry archive cache from the scanned directory

- **ID**: ticket-178
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-20
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION (user requested fixing any demonstrated fixos cleanup failure while preparing the Jetson image)

## Goal and scope

Run the existing Cargo archive cache cleanup directly. Cargo rejects `cargo clean --registry`,
so the current command only cleans through the fallback and reports the unsupported flag.

## Acceptance criteria

- [x] AC-01: The generated Cargo cleanup command targets the registry archive cache directly.
- [x] AC-02: The targeted regression test verifies the exact cleanup command.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

<!-- ticket-radar:start -->
## Ticket Radar

Initial planned-scope estimate; advisory only, not execution or merge approval.

| Measure | Initial assessment |
| --- | --- |
| Impact score | 56/100 |
| Complexity | M |
| Estimated effort | 59 min |
| Planning budget | 30 min |
| Split recommended | yes |

Diagnostics: RADAR-ACCEPTANCE-MISSING, RADAR-BUDGET-EXCEEDED.
<!-- ticket-radar:end -->
