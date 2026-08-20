# Ticket 003: Optimize stale Docker startup workloads

- **ID**: ticket-003
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-20

## Goal and scope

Add a conservative Docker startup optimizer to FixOS. It identifies containers
that are configured to start automatically, maps them to a Git repository by
Docker Compose metadata or bind mounts, and proposes disabling startup only
when the repository is clean and has had no commit for a configurable period.

The optimizer is dry-run first. Applying a result requires an exact container
selection; stopping a currently running container is a separate explicit
option. Containers, images, networks and volumes are never deleted.

## Acceptance criteria

- [x] AC-01: Scanning reports startup-enabled containers, their exact
  repository evidence, Git inactivity, state and associated `docker exec`
  helper processes.
- [x] AC-02: A container is a stale candidate only with an `always` or
  `unless-stopped` restart policy, an unambiguous existing Git repository, a
  clean worktree and no commit within the configured minimum age.
- [x] AC-03: Missing repository evidence, Git errors, dirty worktrees, recent
  commits and non-startup restart policies fail closed.
- [x] AC-04: Optimization is dry-run by default and requires exact candidate
  IDs. Applying it changes only the restart policy to `no`; stopping an active
  (`running`, `restarting` or `paused`) candidate requires a separate opt-in.
- [x] AC-05: No code path removes containers, images, volumes or networks, and
  deterministic tests verify mutation commands and safety refusals.
- [x] AC-06: A read-only scan of the current Docker daemon and the focused,
  full and governance test suites pass.
- [x] AC-07: Running `fixos` advertises stale Docker services and
  `fixos cleanup --docker-stale-services` provides a 3-day-default preview,
  numbered exact selection, autostart confirmation and separate stop-now
  confirmation.
- [x] AC-08: CLI dry-run/list/JSON modes do not mutate Docker, conflicting
  destructive Docker modes are rejected, and focused CLI tests verify exact
  IDs passed to the optimizer.

## Validation result

- The focused optimizer suite passed 10/10 and static checks reported no issues.
- The final independent worktree suite passed with 470 tests, 5 skips and 16 intentional
  deselections.
- A read-only live scan inspected 191 containers and mapped all 103 persistent
  `docker exec` helpers. It proposed only three containers from the clean
  `cybermysz-pl` repository, whose last commit was 35.9 days old.
- No live Docker restart policy, container state, process or repository was
  changed during the initial validation dry run.
- The Docker ticket and the earlier PyCharm ticket were placed in separate
  worktrees; governance passed with 0 errors and 0 warnings in both.
- With the user's explicit authorization, a 3-day live run selected 13 clean,
  repository-backed services. All now have `restart=no` and `exited`; no
  container, image, network or volume was deleted.
- Ten associated `docker exec` helpers exited, reducing their system-wide count
  from 102 to 92. A `restarting` service exposed a stop-state bug; it was
  stopped by exact full ID, the active-state logic was corrected and a
  regression test was added.
- PyCharm remained alive and its thread count fell from 884 to 843, but five
  later CPU samples still averaged 494.9%, so Docker cleanup alone is not
  claimed to have resolved the IDE contention.
- The welcome screen now advertises `--docker-stale-services`. The command uses
  a 3-day default, supports `--days`, numbered/range/all selection, and asks
  separately before changing restart policy and stopping active services.
- CLI and optimizer focused tests passed 31/31. The final full suite passed 474
  tests with 5 skips and 16 intentional deselections; governance passed with 0
  errors and 0 warnings.
- A live source-tree dry run showed 0 remaining candidates and 92 helpers and
  made no changes. The pre-publication installed executable was correctly
  identified as stale and is updated only after the governed revision is
  published.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
