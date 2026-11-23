# Ticket 182: Add deterministic DNS diagnostics and repair command (fixos dns and auto plugin)

- **ID**: ticket-182
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Explicit user request in active session to add deterministic DNS diagnostics and repair (`fixos dns` CLI command + built-in `dns` diagnostic plugin registered in `PluginRegistry` for `fixos auto`, `fixos scan`, and `fixos fix`).

## Acceptance criteria

- [x] AC-01: Built-in `dns` plugin detects `/etc/resolv.conf` issues, high `systemd-resolved` timeout counts, router-only default-route DNS links, and host resolution failures/latency.
- [x] AC-02: `fixos dns` supports `--fix`, `--yes`, `--dry-run`, `--host`, `--dns`, and `--json`, and `PluginRegistry` registers `dns` automatically.
- [x] AC-03: Unit tests in `tests/unit/test_dns_plugin.py` and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
