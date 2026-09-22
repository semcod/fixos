# Ticket 051: cleanup: odzyskiwanie miejsca - snap revizje, journal, cache, JetBrains, libvirt, gitive-isolated

- **ID**: ticket-051
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

Extend `fixos cleanup` with disk-space reclaim actions for the large
consumers identified during the full-disk investigation
(`/` at 100 %): old snap revisions, systemd journal, user caches,
JetBrains leftovers, unused libvirt images and stale gitive-isolated
workspaces. Each action lists candidates with sizes, then removes only
the explicitly selected entries (or all with `--yes`).

SESSION_EXECUTION_AUTHORIZATION: the user's request "dodaj wiecej opcji
dla cleanup w menu ... ale bez videos i downloads" authorizes this
implementation. `~/Videos` and `~/Downloads` are explicitly out of
scope and are never scanned for deletion.

New options:

- `fixos cleanup --snap-old` — remove disabled snap revisions
  (`snap list --all` rows with `disabled`, deleted via
  `snap remove --revision`).
- `fixos cleanup --journal` — show `journalctl --disk-usage` and vacuum
  to a chosen size (`journalctl --vacuum-size=`).
- `fixos cleanup --user-cache` — select oversized `~/.cache` subtrees
  and remove them (regenerable cache only).
- `fixos cleanup --jetbrains` — remove stale JetBrains Toolbox channels
  (`ch-*` older than the newest per app) and `~/.cache/JetBrains` data;
  IDE settings in `~/.local/share/JetBrains/<IDE>` are preserved.
- `fixos cleanup --libvirt` — remove `~/.local/share/libvirt` images not
  attached to any defined libvirt domain.
- `fixos cleanup --gitive` — remove `~/.local/share/gitive-isolated`
  workspaces not referenced by a running or stopped container.
- `fixos cleanup --docker-buildcache` — prune the cache of every buildx
  builder listed by `docker buildx ls`, including docker-container
  driver instances (e.g. `arm64-builder`) that the default
  `docker builder prune` / `--docker-all` path never touches, plus
  dangling `<none>` images via `docker image prune`.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (user request above).
- [x] AC-02: `pytest -q tests/unit/test_cleanup_space.py` passes.
- [x] AC-03: `pytest -q tests/unit/` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
