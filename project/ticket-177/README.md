# Ticket 177: Honor explicit zero when scanning service caches for cleanup

- **ID**: ticket-177
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-20

## Goal and scope

The operator requested investigation and repair of FixOS disk reclamation (SESSION_EXECUTION_AUTHORIZATION). An explicit zero size filter currently hides small service caches. Honor that filter in service inventory and preserve the default when no threshold was supplied.

## Acceptance criteria

- [x] AC-01: A small cache appears with a zero threshold and stays below the default threshold. The regression failed on the accepted base and passed after the change.
- [x] AC-02: The scanner, cleanup, virtualenv and reclamation suites passed (141 tests). The `cleanup -c pip --threshold-gb 0 --dry-run` preview recognized the cache.

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
