# Ticket 147: Add POSIX sh fallback for Python-less SSH peers in mesh diagnostics

- **ID**: ticket-147
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user asked to execute
  backlog tasks for `semcod/fixos` and verify proper operation (`docs/information/mesh.md`
  `next_actions`, 2026-11-18).

## Goal and scope

Implement the `docs/information/mesh.md` backlog item for Python-less SSH peers
(such as OpenWrt routers and BusyBox appliances):
- When `ssh -o BatchMode=yes ... python3 -c ...` fails because `python3` is
  missing on the remote peer (`rc == 127` or `"python3: not found"`), fall back
  to a bounded, strictly input-validated POSIX `sh` probe (`REMOTE_POSIX_SH_PROBE`)
  using `uname -n`, `getent`/`nslookup`, `ip -4 route get`, and `nc -z` (or
  `ping -c 1` if `nc` is absent).
- Do not retry when SSH transport/authentication itself fails (`rc == 255`).

## Acceptance criteria

- [x] AC-01: Python-less SSH peers fall back to `REMOTE_POSIX_SH_PROBE` and
      report active `open_ports`/`closed_ports` or `ping_ok` results, while SSH
      transport/auth failures (`rc == 255`) do not trigger a second SSH call.
- [x] AC-02: Unsafe target hostnames are rejected before constructing remote
      shell probes, and unit tests verify both direct `sh -c` execution and SSH
      fallback behavior.
- [x] AC-03: Governance check and Ruff pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
