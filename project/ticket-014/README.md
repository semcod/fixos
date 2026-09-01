# Ticket 014: Prove manifest-driven FixOS PR automation

- **ID**: ticket-014
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-01

## Goal and scope

Prove that the deployed manifest profile for `semcod/fixos` handles a real
FixOS pull request end to end: Goal publishes an exact ticket head, OneDev
performs its isolated local checks and Validator Agent independently binds its
review and merge decision to that unchanged head.

The proof is governance-only. It must not alter FixOS executable source,
tests, dependencies, required hosted checks or protected merge authority.

## Acceptance criteria

- [x] AC-01: The user's autonomous execution and `goal -a` request is recorded
  as `SESSION_EXECUTION_AUTHORIZATION` for this bounded proof.
- [x] AC-02: The candidate diff contains governance evidence only and does not
  alter executable FixOS behavior or merge policy.
- [x] AC-03: `goal -a` publishes one exact ticket head and all required hosted
  FixOS checks pass for that head.
- [x] AC-04: The deployed OneDev profile automatically reports
  `onedev/local-verify=PASS` and dispatches the same repository, PR, ticket and
  HEAD to Validator Agent.
- [x] AC-05: The trusted Validator App approves and merges the exact head, and
  the ticket branch is deleted after merge.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
