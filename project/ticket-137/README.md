# Ticket 137: Document host anomaly detection and release 2.4.0

- **ID**: ticket-137
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-16

## Goal and scope

`fixos anomalies` (ticket-136) and the artifact store reclaim (ticket-135) are
merged but unreleased: the package version is still 2.3.0, so an installed
fixOS does not have them.

Scope: add `docs/information/host-anomalies.md` describing the command, its
categories, removal guards and limits, and raise `VERSION` and
`pyproject.toml` to 2.4.0. No code changes. `CHANGELOG.md` is owned by the
governance workstream and is not touched here.

## Acceptance criteria

- [x] AC-01: `python -m fixos.cli --version` reports 2.4.0 from the ticket worktree.
- [x] AC-02: The document follows the repository docs format (front matter and
      the seven `docs:section` markers) and states only verified results.
- [ ] AC-03: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
