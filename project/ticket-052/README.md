# Ticket 052: Stale venv cleanup and Rust scanning integration

- **ID**: ticket-052
- **Owner**: codex:fixos-052-20260928
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested startup-menu cleanup of venv/ and .venv/ older than 30 days in inactive projects, selectable age and complete totals before removal; extract scanning code into new Rust packages and integrate them for speed. Work is local, with benchmarks before any speed claim.

Use project source metadata, environment metadata and process observations conservatively. Unknown activity, symlinks, missing virtualenv markers and observation errors exclude deletion. Default root is ~/github; root is configurable. Revalidate immediately before selected removal. Never execute cleanup on the user's projects as part of development.

New Rust repository: proposed semcod/fixos-native, independent ownership/ticket and library + CLI packages. FixOS integration uses an optional native backend and retains a Python fallback.

## Acceptance criteria

- [x] AC-01: Menu and CLI expose default 30 days and custom positive period, complete inventory/count/size, selection, confirmation and dry-run.
- [x] AC-02: Recent projects/environments, active processes, symlinks, unreadable trees and changed candidates are protected; focused tests and managed governance pass.
- [x] AC-03: Rust library and CLI packages in a separate repo, integrated native/fallback parity and measured benchmark.

## Delivery

Local validation: 619 unit/CLI tests passed (including native/Python parity), Ruff passed, and the managed governance gate passed. Native ticket-001 has 5 passing Rust tests, Clippy and its governance gate. The warm-cache 50,000-file measurement benchmark observed 0.521 s Python versus 0.099 s Rust (5.25x); this is a fixture result, not a whole-CLI speed guarantee. Native discovery was slower (4.94 ms Python versus 7.67 ms Rust) and is opt-in; heavy tree measurement is automatic when the CLI is installed.

New local repository: semcod/fixos-native, canonical linked checkout ticket-001--filesystem-scanner. It contains fixos-fs and fixos-native packages, installation/protocol documentation, and a reproducible benchmark. Set FIXOS_NATIVE_BIN to its target/release/fixos-native executable, or install the CLI on PATH. FIXOS_NATIVE=off forces the fallback.

No user-project environments were removed. All destructive tests used temporary fixtures. No push, PR, merge or deployment performed; local source commits are the delivery boundary for this session. Preserve both implementation worktrees for review/publication under separate authority.
