# Ticket 025: Make fixos cleanup safe: honor dry-run, truthful sizes, quoted commands

- **ID**: ticket-025
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
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

- [x] AC-01: Focused tests prove that interactive `--dry-run` never executes a
  cleanup, logs no longer cover `~/.local/state`, Discord/Slack commands split
  into only absolute paths, gcloud cleanup does not revoke credentials, a
  non-zero `du` total is used, and a failed `docker system df` runs once and
  appears as a plan warning.
- [x] AC-02: The full test suite and the governance gate passed for exact head
  `0529e6be`. PR #48 CI (governance, Python 3.10/3.11/3.12 and five
  distribution containers) passed; the local Python 3.13 suite recorded
  `612 passed, 5 skipped, 16 deselected`.

## Publication evidence

Trusted Validator App review approved exact head `0529e6be` after
`onedev/local-verify=SUCCESS` and merged PR #48 into `main` as `9ad62df`.
The remote ticket branch was deleted by the repository merge policy.

## Publication evidence

The material implementation and regression test were merged through protected
Validator review as PR #52: exact head `233a46bcb2b73ebbbea34d2fe27b08d42d2e035b`,
merge commit `979022dc698fa95c5ebb6d5e4eeb6abad4def547`. GitHub deleted the
merged remote branch under `delete_branch_on_merge=true`. Post-merge governance
and lifecycle checks passed on `main`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
