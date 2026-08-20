# Ticket 008: Expose JetBrains doctor CLI

- **ID**: ticket-008
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-20

## Goal and scope

Expose the existing JetBrains JVM diagnosis and window-preserving recovery as
an explicit FixOS command. The doctor must discover main IDE processes, report
metrics, heap, EDT and recent log evidence, recognize the observed AI quota
refresh loop, and remain read-only unless the user explicitly requests a
diagnosis-justified GC for one exact PID.

## Acceptance criteria

- [x] AC-01: `fixos jetbrains doctor` discovers and diagnoses main JetBrains
  processes without closing windows or changing configuration.
- [x] AC-02: Human and JSON output include PID identity, severity, CPU, RSS,
  threads, heap pressure, EDT state, reason codes, log signals and errors.
- [x] AC-03: Repeated JetBrains AI quota failures are counted and reported as a
  distinct reason without being treated as evidence that GC is justified.
- [x] AC-04: `--apply-gc` requires one explicit PID, current diagnostic
  justification and an interactive confirmation unless `--yes` is supplied.
- [x] AC-05: Empty, invalid PID, diagnosis, dry-run and applied-result paths are
  covered by deterministic CLI tests; existing recovery safety tests remain.
- [x] AC-06: The root menu and command help expose the doctor, and focused,
  full, lint, compile and governance validation pass before publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
