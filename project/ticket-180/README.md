# Ticket 180: Expose read-only process anomalies to HostGuard

- **ID**: ticket-180
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-21

## Goal and scope

Allow HostGuard to collect process anomaly evidence even during severe disk
pressure. Reuse FixOS's read-only process scanner and retain the ordinary
full report, directory-removal options, and JSON envelope.

SESSION_EXECUTION_AUTHORIZATION: the user requested host resource diagnostics
and improvements to Bottlenecks and FixOS for HostGuard on 2026-11-22.
Planfile request PLF-21844. This slice changes only the CLI and a separate
test, preserving ticket-161's reservation on the underlying scanner.

## Acceptance criteria

- [x] AC-01: The session authorizes the scoped implementation and protected publication.
- [x] AC-02: Process-only JSON returns process evidence without starting storage inventory.
- [x] AC-03: Process-only mode rejects removal options before scanning.
- [x] AC-04: The existing full report and removal behavior have regression coverage.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

<!-- ticket-radar:start -->
## Ticket Radar

Initial planned-scope estimate; advisory only, not execution or merge approval.

| Measure | Initial assessment |
| --- | --- |
| Impact score | 52/100 |
| Complexity | M |
| Estimated effort | 51 min |
| Planning budget | 30 min |
| Split recommended | yes |

Diagnostics: RADAR-ACCEPTANCE-MISSING, RADAR-BUDGET-EXCEEDED.
<!-- ticket-radar:end -->
