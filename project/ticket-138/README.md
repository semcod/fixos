# Ticket 138: Report partial removals truthfully and remove read-only directories in fixos anomalies

- **ID**: ticket-138
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-16

## Goal and scope

First live use of `fixos anomalies --remove` (2026-11-16) removed four of seven
selected directories. The other three failed with EACCES and were reported as
`pominięto … (os_error:13)`, although `shutil.rmtree` had already deleted part
of each: 2.8, 2.6 and 1.1 GiB trees were left at 1950, 478 and 656 MiB. One of
them held 227 read-only directories owned by the user; the other two held 10
and 12 files owned by another account.

Scope: make user-owned read-only entries writable and retry once; report a
tree that still exists after the attempt under a new `partial` list with the
reason and remaining bytes, and count the bytes actually freed.

## Acceptance criteria

- [x] AC-01: A tree with read-only directories owned by the user is removed completely.
- [x] AC-02: A tree with an entry that cannot be unlinked is reported under
      `partial` with `remaining_bytes`; it is in neither `removed` nor `refused`,
      and a receipt is written.
- [x] AC-03: 12 unit tests, `ruff check` and `ruff format --check` pass.
- [ ] AC-04: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
