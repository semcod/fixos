# Ticket 004: Clean orphaned project workloads

- **ID**: ticket-004
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-20

## Goal and scope

Add an explicit FixOS cleanup flow for workloads whose project directory no
longer exists and for stale IDE-agent or local development-server process
trees. The flow must remain read-only by default, show exact Docker and PID
evidence, protect the calling process ancestry, and require explicit selection
before it disables Docker restart policies, stops containers, or terminates a
process tree.

The authorized live run targets the 30 running Compose containers whose
recorded working directories for `dbos`, `codot`, `redsl` and `todo2code` no
longer exist, the two inactive PyCharm Cursor ACP backends rooted at PIDs
`810433` and `3051859`, and the explicitly identified client-free development
servers on ports `8781`, `8782`, `8099`, `8105` and `8793`. Docker objects,
volumes and project files are retained.

## Acceptance criteria

- [x] AC-01: Read-only scanning reports startup-enabled Compose containers
  whose absolute working-directory label is missing and whose container age
  exceeds the configurable threshold.
- [x] AC-02: Scanning reports stale IDE-agent and local development-server
  process trees with PID identity, age, command, descendants, memory and TCP
  connection/listener evidence.
- [x] AC-03: The current FixOS ancestry, privileged/system processes, the main
  JetBrains JVM and current Codex processes are protected from termination.
- [x] AC-04: Applying an exact Docker selection only sets `restart=no` and
  stops the selected containers; it never removes containers, images,
  networks, volumes or files.
- [x] AC-05: Applying an exact process selection revalidates PID creation time,
  terminates leaves before the root and makes force escalation a separate
  opt-in.
- [x] AC-06: `fixos`, `fixos cleanup --help`, list/dry-run/JSON modes and the
  interactive cleanup flow expose the orphaned-project action and describe
  its expected result.
- [x] AC-07: Deterministic tests cover missing/existing/young/relative Compose
  paths, exact Docker commands, candidate process evidence, PID reuse,
  ancestry protection, CLI routing and non-mutating modes.
- [x] AC-08: The authorized live cleanup is verified with the selected Docker
  containers stopped at `restart=no`, selected process trees absent, protected
  applications alive and no Docker data removed.
- [x] AC-09: Focused, full and governance validation pass before publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
