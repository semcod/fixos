# Ticket 135: Reference-aware artifact store and system-wide reclaim cleanup

- **ID**: ticket-135
- **Owner**: agent:cline
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-11

## Goal and scope

A manual content-addressed store cleanup removed
`inputs/sha256/<digest>/builder-kernel`, which `inputs/runtime/<sha>/guestfs.json`
references only by absolute path, and the image build then failed with
"Guestfs kernel/modules missing". This ticket teaches fixOS to reclaim such
stores safely and to analyse system-wide reclaimable data without touching
private user directories.

## Acceptance criteria

- [x] AC-01: `fixos cleanup -c artifacts` inventories `sha256/<digest>/` entries and
      protects every entry referenced by a manifest digest, an absolute path in a
      manifest, a symlink, the Git index or an earlier receipt.
- [x] AC-02: `--artifacts-system-wide` inventories an allowlist of system caches
      (apt archives, crash/coredump, rotated logs, tmp, pip/uv/npm caches,
      thumbnails, trash, journal) operating on directory contents only.
- [x] AC-03: private home directories (Downloads, Documents, Pictures, …) and
      credential stores are never candidates; every removal writes a
      `fixos.artifact-reclaim/v1` receipt.
- [x] AC-04: 12 unit tests pass (`tests/unit/test_artifact_store.py`).
- [ ] AC-05: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
