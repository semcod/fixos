# Ticket 009: Persist orphan project pins

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-20

## Goal and scope

Add a persistent, user-managed list of missing Compose project directories
whose containers must remain protected. The orphan-workload scan must keep
these containers visible as pinned evidence while excluding them from every
cleanup selection and fresh apply-time revalidation.

## Acceptance criteria

- [x] AC-01: FixOS stores absolute, non-root project paths atomically under the
  user's XDG configuration directory and fails closed on invalid state.
- [x] AC-02: `fixos cleanup` can pin, list and unpin project paths without
  changing Docker or processes.
- [x] AC-03: Containers whose Compose working directory matches a pin remain
  visible as protected/pinned records but never appear in `docker_candidates`.
- [x] AC-04: Cleanup performs a fresh scan through the same pin provider, so a
  selected container cannot bypass a pin added before apply.
- [x] AC-05: Command help and human/JSON results describe the persistent state
  and the absence of Docker deletion.
- [x] AC-06: Focused, full, lint, compile and governance checks pass; the live
  `relcom` path is pinned and a read-only scan reports its containers protected.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
