# Ticket 115: Keep default cleanup proposal tests independent of live Docker

- **ID**: ticket-115
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

The full protected delivery preparation for ticket-114 stopped at a 30-second
unit-test timeout: a fake Docker proposal fixture escaped to live buildx du.
Inject the missing BuildKit measurement and prove the real inventory boundary
is never invoked. Preserve all existing proposal assertions and test deadlines.

SESSION_EXECUTION_AUTHORIZATION: the user requested continuing repairs and
merges on 2026-10-31. This separate, disjoint test correction is a prerequisite
for ticket-114 and includes independent exact-head protected publication.

## Acceptance criteria

- [x] AC-01: Default-proposal tests cannot invoke the live BuildKit inventory.
- [ ] AC-02: Affected and complete tests plus managed governance pass.
- [ ] AC-03: Independent exact-head protected publication succeeds.

## Validation

The new boundary regression failed against the baseline with one live inventory
invocation. All 29 tests in the affected file now pass with their original
assertions and deadlines. Changed-file Ruff passed. The full suite, required
Python matrix and independent review remain publication work.
