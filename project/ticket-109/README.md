# Ticket 109: fix(quick): suppress false-positive critical disk alert when absolute free space exceeds safe threshold on multi-TB filesystems

- **ID**: ticket-109
- **Owner**: agent:agy
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

On large filesystems (e.g. 2 TB NVMe where 5% reserved blocks + 93-95% usage still leaves > 100 GB of available disk space), `fixos/diagnostics/quick_snapshot.py` (`_alerts`) triggers a `CRITICAL` disk alert purely based on `disk['percent'] >= disk_critical` without accounting for large absolute free space.

Downgrade `critical` disk alerts to `warning` in `_alerts` when `disk['free_bytes'] >= 50 * 1024**3` (50 GiB), and include the human-readable free GB in the alert message so operators on multi-TB drives get accurate severity classification. Add unit tests covering alert severity on both small and multi-TB filesystems.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner (GitHub issue semcod/fixos#133 / PLF-20296).
- [x] AC-02: `_alerts` in `fixos/diagnostics/quick_snapshot.py` downgrades critical disk alert to warning when `free_bytes >= 50 * 1024**3`, formatting free space in GB in the message.
- [x] AC-03: Unit tests in `tests/unit/test_quick_snapshot.py` verify alert severity and message on small and multi-TB filesystems.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
