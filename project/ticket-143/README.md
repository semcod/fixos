# Ticket 143: Fix remote SSH argv, port validation, and USB queue filtering in mesh CLI

- **ID**: ticket-143
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — follow-up defect fixes
  for the authorized mesh host diagnostics delivery (2026-11-18).

## Goal and scope

Fix three post-review defects found in `ticket-142`:
1. `_exec_ssh_probe` passed `--` after `python3 -c "..."`, shifting `sys.argv`
   on remote SSH peers (`sys.argv[1] == "--"`) and use explicit `struct.pack`
   for the mDNS trailer in `REMOTE_PYTHON_PROBE`.
2. `parse_ports` in `fixos/cli/mesh_cmd.py` raised raw `ValueError` instead of
   `click.BadParameter` on non-numeric `--ports` input.
3. `fixos/cli/printers_cmd.py` `--mesh` fallback parsed `usb://...` URIs as
   network hostnames instead of delegating to `PrinterQueue.host`.

## Acceptance criteria

- [x] AC-01: Unit tests cover `REMOTE_PYTHON_PROBE` argv/packet execution,
      non-numeric `--ports` `click.BadParameter`, and `usb://` queue filtering.
- [x] AC-02: Live `fixos mesh 192.168.188.158` executes active SSH probe on
      remote peer `minis` (`192.168.188.80`) with `63f4612` argv regression fixed.
- [ ] AC-03: Governance check, Ruff, and Wellman check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
