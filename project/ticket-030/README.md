# Ticket 030: Adopt Git ancestry for ticket activity resolution

- **ID**: ticket-030
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the human repeatedly requested continuation,
implementation and testing of the FixOS governance work. The fresh integrated
`main` tree reproduces a lifecycle defect: `goal -a` treats merged tickets as
active because the repository ticket-activity registry is external and the
target has no projection override. This leaves stale base, delivery-budget and
workstream findings after protected merge.

Adopt the target-owned `git-ancestry` activity policy used by the current Goal
repository. The resolver will infer that a ticket whose directory is integrated
on `main` and has no unmerged ticket branch is inactive, while keeping an
unmerged implementation branch active. This ticket changes one governance
configuration file and records the bounded validation evidence.

The allocator reported `ticket-029` as an active governance conflict even
though its work is already integrated. The human continuation authorization
therefore explicitly covers the allocator's `--force-new` allocation for this
distinct corrective workstream task; it does not authorize any ticket closure
or bypass of governance validation.

## Acceptance criteria

- [x] AC-01: The failure on a fresh integrated `main` tree is reproduced and
  the resolver's external-registry/status projection mismatch is identified.
- [ ] AC-02: `.governance/ticket-activity.override.json` selects
  `missingPolicy: git-ancestry` and stays within the declared intent.
- [ ] AC-03: Managed governance, ticket-activity validation, stack checks and
  a fresh-main `goal -a` run pass after the change.
- [ ] AC-04: The exact material HEAD is published through OneDev and the
  protected Validator flow.

## Validation evidence

- Before the change, fresh integrated `main` reported `GOV-BASE-001`,
  `GOV-DELIVERY-001` and `GOV-WORKSTREAM-002` for already merged tickets.
- The adopted policy is the same target-owned override already used by the
  Goal repository for its merged-ticket activity resolver.
- The ticket-activity validator and managed governance gate pass on the
  material HEAD. The local Python 3.13 suite reports `611 passed, 5 skipped,
  16 deselected` and four pre-existing Click 8.3 compatibility failures in
  `tests/unit/test_ask_and_nl_group.py`; no ticket-030 source or test path is
  involved.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
