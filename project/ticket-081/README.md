# Ticket 081: fixos cleanup --docker-volumes: select and remove unused Docker volumes safely

- **ID**: ticket-081
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

On 2026-10-13 the host had 397 unused Docker volumes (89 GB). fixos only
counted them; removing the 18 model volumes (55.5 GB) needed manual
`docker volume rm`. The only volume path in fixos was `cleanup --full`
"Docker Total" → `docker system prune -a --volumes`, which deletes every
unused volume at once, including data such as git mirrors.

`fixos cleanup --docker-volumes` (also `-c docker-volumes`):

- lists unused volumes with name, Compose project, age and size (`du`, then
  non-interactive `sudo -n du`; otherwise "rozmiar nieznany"), largest first;
- `--match ollama,huggingface` and `--days N` filters; `--list`, `--dry-run`,
  `--json`;
- removes only selected volumes, re-checking each is still dangling and not
  referenced by any container right before `docker volume rm`;
- `--yes` never selects names that look like data (mirror, git, db, postgres,
  backup, ...); those need an explicit choice.

`--full` "Docker Total" now runs the bounded build-cache prune and points to
`--docker-volumes` for volumes.

SESSION_EXECUTION_AUTHORIZATION: user answered "tak" to adding this command to fixos.

## Acceptance criteria

- [x] AC-01: tests cover listing/sorting, filters, `--yes` protection, removal-time re-check, dry-run/list and the `--full` command.
- [x] AC-02: full suite, ruff on changed files and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
