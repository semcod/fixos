# Ticket 186: Fix non-interactive --yes handling in cleanup_cmd and dns_cmd/dns plugin

- **ID**: ticket-186
- **Owner**: agent:antigravity (SESSION_EXECUTION_AUTHORIZATION from user request)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23

## Goal and scope

Fix two live non-interactive hangs observed during autonomous `fixos` execution:
1. Pass `yes=req.yes` to `_cleanup_single_service` in `fixos/cli/cleanup_cmd.py` so `fixos cleanup -c docker --yes` skips `click.confirm(...)`.
2. Guard `fixos dns --fix` against hanging in non-TTY / `fixos auto --yes` mode by refusing interactive `click.confirm` without `--yes`, injecting `sudo -n` in `apply_dns_repair` when non-interactive, and emitting `fixos dns --fix --yes` from `fixos/plugins/builtin/dns.py`.

## Acceptance criteria

- [x] AC-01: `fixos cleanup -c docker --yes` executes without prompting `click.confirm`.
- [x] AC-02: `fixos dns --fix` in non-TTY without `--yes` fails fast without blocking, and `apply_dns_repair(..., non_interactive=True)` uses `sudo -n`.
- [x] AC-03: Unit tests in `tests/unit/test_cleanup_cmd.py`, `tests/unit/test_dns.py`, and `tests/unit/test_dns_plugin.py` pass alongside `./project/governance-check.sh`.
