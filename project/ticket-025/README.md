# Ticket 025: Make fixos cleanup safe: honor dry-run, truthful sizes, quoted commands

- **ID**: ticket-025
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

On 2026-09-15 the user asked to run `fixos cleanup` and check whether it works
correctly, then approved fixing the defects found
(SESSION_EXECUTION_AUTHORIZATION). A read-only `fixos cleanup --list` run and
mocked CLI checks on the developer machine showed:

1. `fixos cleanup --dry-run` without `-c` executes the selected cleanup for
   real: the interactive executors pass `dry_run=False`.
2. The logs service measures all of `~/.local/state` (83 GB, mostly agent
   state) as "safe", while its command removes only `*.log` files older than
   seven days (about 20 MB), so the safe total is inflated about sixfold.
3. The Discord and Slack cache commands contain unquoted `Code Cache` and
   `Service Worker` paths, so the shell passes bare `Cache` and `Worker`
   arguments to `rm -rf` relative to the current directory.
4. The "safe" gcloud cache command revokes application-default credentials.
5. A `docker system df` timeout (90 s; 4.5 min on this host) is not cached, is
   retried within one scan and silently drops about 375 GB of Docker data from
   the report.
6. `du` output with a non-zero exit (one unreadable subdirectory) is discarded
   and the tree is walked again in Python.

Non-goals: no change to the dedicated Docker, Ollama, orphaned-project or
network flows, no new CLI option and no real deletion during validation.

## Acceptance criteria

- [ ] AC-01: Focused tests prove that interactive `--dry-run` never executes a
  cleanup, logs no longer cover `~/.local/state`, Discord/Slack commands split
  into only absolute paths, gcloud cleanup does not revoke credentials, a
  non-zero `du` total is used, and a failed `docker system df` runs once and
  appears as a plan warning.
- [ ] AC-02: The full test suite and the governance gate pass for the exact
  head.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
