# Ticket 072: docs for hardlink-aware freed space and scan performance; release 2.2.53

- **ID**: ticket-072
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

- Compact v2 documents (`wellmanifest/docs` 19efafb):
  [BUGFIX](../../docs/BUGFIX/CLEANUP_HARDLINK_FREED_SPACE.md) for ticket-069 and
  [SERVICE](../../docs/SERVICE/SCAN_PERFORMANCE.md) for ticket-070, linked from
  `docs/README.md`.
- Release projection: `VERSION` and `pyproject.toml` declare 2.2.53, packaging
  tickets 069-071. `goal -a --bump patch` could not do it: goal 2.2.0 rejects
  fixos's computed-version `setup.py` ("selector version was not found"),
  fixed in semcod/goal#188. As in ticket-067 the carriers are bumped here;
  registry publication runs after merge via `goal -a --delivery-mode
  publish-only` once goal#188 is merged.

The docs checker passes both deliverables; its remaining findings concern the
managed `.governance/docs/SNAPSHOT_MIGRATION.md` from the new-project package,
which cannot be edited locally without breaking the managed digest.

SESSION_EXECUTION_AUTHORIZATION: user requested a version bump and publication through `goal -a`.

## Acceptance criteria

- [x] AC-01: both documents exist, are indexed and pass `docs/standard/check.py`.
- [x] AC-02: `test_version_parity.py` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
