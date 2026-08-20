# Ticket 006: Document orphaned workload cleanup

- **ID**: ticket-006
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-20

## Goal and scope

Document the integrated `fixos cleanup --orphaned-projects` workflow in the
getting-started guide. The page must let an operator understand what appears in
the main FixOS menu, how to preview evidence, how exact selection and
confirmations work, what changes after execution and which Docker/application
data remains untouched.

## Acceptance criteria

- [x] AC-01: The user explicitly requested help and updated usage/result
  documentation for the integrated cleanup function.
- [x] AC-02: The guide shows list, dry-run, JSON, interactive and alias usage
  with the default three-day Docker and twelve-hour process thresholds.
- [x] AC-03: The guide explains the Docker and process candidate criteria,
  protected processes, numbered selection and independent confirmations.
- [x] AC-04: The guide states the exact result: selected containers become
  stopped at `restart=no`, selected process trees end leaves-first, and Docker
  objects, volumes, images, networks and project files are retained.
- [x] AC-05: Documentation and governance validation pass before publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
