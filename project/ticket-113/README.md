# Ticket 113: Report Docker dangling-image reclaimability honestly

- **ID**: ticket-113
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

On this host FixOS advertised 22.6 GB of dangling images as reclaimable, but
Docker prune reclaimed 0 B. Three 7 GB images were still referenced by running
containers. Exclude referenced images from the prune inventory and distinguish
logical image sizes from unknown shared-layer reclaimability. A missing
BuildKit reclaimable measurement must remain unknown.

SESSION_EXECUTION_AUTHORIZATION: the user requested continuing FixOS repairs,
cleanup and protected publication on 2026-10-31. This bounded diagnostic repair
uses that authority; independent approval and merge remain controller-owned.

## Acceptance criteria

- [x] AC-01: Images referenced by running or stopped containers are excluded;
  failed usage reads and shared-layer totals never claim known reclaimability.
- [x] AC-02: Missing BuildKit reclaimable measurements remain unknown; CLI and
  JSON output distinguish unknown amounts; existing safe prune commands remain.
- [ ] AC-03: Local checks pass and exact-head independent publication is requested.

## Validation

- Nine regression cases failed before the fix; all 10 now pass.
- Focused cleanup suites: 32 passed. Ruff, import sorting and managed governance passed.
- Live read-only inventory no longer lists images used by containers as prune candidates.
- Full governed checks and exact-head independent publication run through Goal and the protected Validator.
