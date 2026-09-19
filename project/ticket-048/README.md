# Ticket 048: Fix disk_analyzer memory explosion and cleanup correctness bugs

- **ID**: ticket-048
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Harden disk analysis and the user-facing cleanup workflow. The change replaces
memory-heavy recursive scans with bounded traversal, reuses one scan result per
analysis, prevents cleanup suggestions from pruning Docker volumes, protects
offline Spotify data, bounds discovered-cache paths, and strips terminal escape
sequences before Click validates interactive choices.

## Acceptance criteria

- [x] AC-01: Scope is approved by the requesting human owner.
- [x] AC-02: Cleanup and disk-analyzer regressions pass locally.
- [ ] AC-03: Protected CI and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
