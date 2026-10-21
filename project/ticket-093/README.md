# Ticket 093: Target-driven cleanup that reclaims disk until a free-space goal is met

- **ID**: ticket-093
- **Owner**: agent:opencode.glm-5.3
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-21

## Goal and scope

`fixos cleanup --threshold-gb 10` (the invocation suggested by the NoLimits
LIM-STORAGE-001 runbook) sets a *per-service scan threshold*, not a free-space
goal: with it, only services larger than 10 GB are even reported, and on this
host those are exactly the protected ones (Ollama models, snap). `--yes` then
cleans just the small safe caches and stops far below a safe margin while the
real reclaimable pools are never touched.

This ticket adds a target-driven mode:

- `fixos cleanup --free-gb N` (alias `--target-free-gb`) — reclaim until
  `statvfs('/')` free space reaches N GB, using a bounded ladder of
  no-privilege tiers, stopping at the goal:
  1. safe service caches (existing `--yes` plan),
  2. stale `/tmp` entries (existing `_cleanup_tmp`, default 3 days),
  3. stale agent release caches `~/.local/share/*/releases|release|snapshots/*`
     untouched for 7+ days (new; read-only/protected directories are skipped),
  4. Docker dangling images + build cache prune (new; hard 30 s per-call
     timeout so a busy daemon skips the tier instead of hanging),
  5. Docker images unreferenced by any container and older than `--days`
     (default 14) (new, same timeout guard).
- When the goal is still unmet, print the exact privileged next steps (old
  snap revisions, rotated syslog archives) instead of failing silently.
- `--threshold-gb` keeps its per-service meaning; help text now states it is
  not a free-space goal.

## Acceptance criteria

- [ ] AC-01: `python -m pytest tests/unit/test_cleanup_free_target.py tests/unit/test_cleanup_cmd.py tests/unit/test_cleanup_tmp.py -q` passes.
- [ ] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
