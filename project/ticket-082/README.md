# Ticket 082: docker-volumes: measure volume sizes in parallel

- **ID**: ticket-082
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

`fixos cleanup --docker-volumes --list` took ~60 s on a host with 379 unused
volumes, almost all of it in one sequential `sudo -n du` over every mountpoint.
Sizes are now measured in 8 parallel batches; readable mountpoints use plain
`du`, unreadable ones go straight to `sudo -n du`, so a partial size of an
unreadable directory is never recorded.

Same host, same 379 volumes: 47.5 s → 13.0 s, identical 37.4 GB total.

SESSION_EXECUTION_AUTHORIZATION: user selected "Przyspiesz --docker-volumes".

## Acceptance criteria

- [x] AC-01: test proves batching into `_SIZE_WORKERS` calls with full results.
- [x] AC-02: full suite and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
