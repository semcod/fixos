# Ticket 136: Host anomaly detection (restart loops, unrotated container logs, stale state stores, IDE indexes, leaked processes)

- **ID**: ticket-136
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-11

## Goal and scope

Reused from the unassigned allocation "Release 2.4.0 …" (2026-11-11, never
committed), which blocked new allocation. The version bump is out of scope:
`VERSION` and `pyproject.toml` are not owned by the `application` workstream.

On 2026-11-16 a manual host clean-up found causes of load and disk pressure
that `fixos auto` and `fixos cleanup` did not report:

- `k3s.service` restarting in a loop (16 881 restarts) and flooding syslog;
- Docker container logs without rotation (6 GiB, no `log-opts.max-size`);
- large untouched directories in `~/.local/state` (17 GiB of backups from
  October, a 9 GiB retained runtime backup);
- a 22 GiB JetBrains index while the IDE was not running;
- about 420 zombie processes under four container PID 1 processes and 470
  leaked identical helper processes.

Scope: a read-only detector module `fixos/diagnostics/host_anomalies.py` and a
new command `fixos anomalies`. System-level remedies (service changes, log
truncation, signals) stay suggested commands. Removal is limited to
`stale-state` and idle `ide-index` findings that a fresh scan still reports,
inside the user's home, never through a symlink or a protected directory, and
writes a `fixos.host-anomaly-removal/v1` receipt.

## Acceptance criteria

- [x] AC-01: 10 unit tests pass (`tests/unit/test_host_anomalies.py`), covering each
      detector, the false-positive guard for daemons sharing a name, and the
      removal guards (not a current finding, symlink, outside home).
- [x] AC-02: `python -m fixos.cli anomalies` on the live host reported restart
      loops not found manually (`safetytwin-agent`, `minis-ollama-tunnel`,
      `twinerd-minis-novnc`) and the zombie parents.
- [x] AC-03: `ruff check` and `ruff format --check` pass for the three new files.
- [ ] AC-04: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
