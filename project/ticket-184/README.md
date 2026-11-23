# Ticket 184: Enforce wellmanifest git-lifecycle 6 hard vetos in project_scanner

- **ID**: ticket-184
- **Owner**: agent:antigravity (SESSION_EXECUTION_AUTHORIZATION from user request)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23
- **Issue**: semcod/fixos#235

## Goal and scope

Enforce the 6 canonical `wellmanifest/git-lifecycle` hard vetos in
`fixos/diagnostics/project_scanner.py` before proposing directory/worktree
cleanup candidates so protected workspaces always resolve to `HOLD_PROTECTED`
and never emit unsafe deletion commands:

1. Active processes (`/proc/*/cwd`, `/proc/*/fd`, or `lsof` inside target)
2. Active leases (`.subactor/leases/*.json` in active or unreadable/foreign state)
3. Open PRs / unmerged commits (unmerged vs default branch or open PR metadata)
4. Dirty working tree or stashes (`git status --porcelain` / `git stash list`)
5. Unpushed refs / ahead branches (`git rev-list --count @{u}..HEAD` / local-only branch)
6. Active linked worktree / primary checkout / IDE ownership (linked worktrees, primary checkout owning linked worktrees, or IDE lock/session)

## Acceptance criteria

- [x] AC-01: `evaluate_cleanup_vetos` enforces all 6 hard vetos and returns `HOLD_PROTECTED` with structured veto codes and reasons whenever any veto fires.
- [x] AC-02: `scan_project_artifacts` enforces the 6 hard vetos by default and never proposes unsafe `rm -rf` deletion candidates for protected repos/worktrees.
- [x] AC-03: Unit tests in `tests/unit/test_project_scanner.py` verify each of the 6 hard vetos forces `HOLD_PROTECTED` and blocks unsafe deletion proposals.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
