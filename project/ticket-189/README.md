# Ticket 189: enable-idle-takeover-policy

- **ID**: ticket-189
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-27

## Goal and scope

Enable `coordination.idleTakeover` (`enabled: true`, `idleMinutes: 15`, `leaseMinutes: 120`) in `.governance/manifest.json` so declared controller CAS handoff can legally reclaim expired/idle ticket leases.

## Acceptance criteria

- [x] AC-01: `.governance/manifest.json` configures `coordination.idleTakeover` matching `.governance/manifest.schema.json`.
- [x] AC-02: `./project/governance-check.sh` and `wellman check` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

<!-- ticket-radar:start -->
## Ticket Radar

Initial planned-scope estimate; advisory only, not execution or merge approval.

| Measure | Initial assessment |
| --- | --- |
| Impact score | 48/100 |
| Complexity | M |
| Estimated effort | 44 min |
| Planning budget | 30 min |
| Split recommended | yes |

Diagnostics: RADAR-ACCEPTANCE-MISSING, RADAR-BUDGET-EXCEEDED.
<!-- ticket-radar:end -->
