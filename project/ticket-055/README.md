# Ticket 055: Fix stale venvs cleanup false positives from atime and unexcluded metadata

- **ID**: ticket-055
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested investigation and fix for
`fixos > cleanup --venvs-old`, where scanning projects produced 0 eligible
candidates (out of 70 venvs / 24.2 GB) and every venv was protected by
"projekt ma nowszą aktywność, środowisko ma nowszą aktywność".

Fixes:
1. Do not use access time (`atime_ns`) to evaluate staleness for projects or
   virtual environments. On modern Linux filesystems (with relatime), any read
   operation by indexers, search tools, IDEs, or fixos updates atime, making
   atime permanently younger than the cutoff and causing 100% false positive
   protection. Use modification time (`mtime_ns`) for activity and staleness.
2. Exclude non-source metadata directories and synced governance files from
   project activity measurement: VCS metadata (`.git`, `.hg`, `.svn`), IDE
   workspace files (`.idea`, `.vscode`, `.cursor`), daemon/tool metadata
   (`.planfile`, `.koru`, `.governance`, `.subactor`, `.nlp2dsl`), and global
   governance files (`.aider.conf.yml`, `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`,
   `.github`). This ensures background syncs and git operations do not falsely
   flag a dormant project as actively worked on.
3. In `active_paths()`, skip zombie processes and skip processes not owned by
   the current user before probing process fields, preventing noisy AccessDenied
   errors from system daemons or containers.

## Acceptance criteria

- [x] AC-01: Virtualenv staleness and project activity are evaluated using modification time (`mtime_ns`) instead of `atime_ns`.
- [x] AC-02: Project source measurement excludes VCS metadata, IDE state, daemon telemetry, and global governance sync files.
- [x] AC-03: Process observation skips dead zombie processes and non-user processes cleanly without producing extraneous AccessDenied errors.
- [x] AC-04: Unit tests in `tests/unit/test_venv_cleanup.py` are updated and passing.
- [x] AC-05: Ruff checks and governance checks pass.

## Delivery

No user project environments were removed during testing or implementation.
Preserve the existing age threshold and fallback scanner behavior. Focused
venv regressions pass (42 tests in `tests/unit/test_venv_cleanup.py`), cleanup
CLI tests pass (23 tests in `tests/unit/test_cleanup_cmd.py`), Ruff passes, and
`./project/governance-check.sh` passes with 0 errors and 0 warnings. Real-world
dry run on `~/github/semcod` cleanly identified 18 eligible stale
virtual environments (~4.34 GB) instead of 0, with 0 false observation errors.


