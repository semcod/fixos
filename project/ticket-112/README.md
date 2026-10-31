# Ticket 112: Reject unsafe MCP receipt request identifiers before cleanup

- **ID**: ticket-112
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

A controlled dry-run with request_id `../escaped` created a receipt outside the
configured receipt directory. Reject traversal, absolute paths, unsafe portable
filenames and overlong identifiers before receipt lookup, scanning or cleanup.
Retain normal receipt replay and automatically generated identifiers.

SESSION_EXECUTION_AUTHORIZATION: the user requested continuing FixOS repairs
and protected publication on 2026-10-31 after the earlier MCP repair. This is a
bounded correction to the same MCP cleanup interface. Prior publication actor
mismatches remain historical evidence and do not grant approval authority.

## Acceptance criteria

- [x] AC-01: Invalid request IDs fail before receipt directory access or cleanup,
  for both dry-run and real execution; JSON-RPC reports an error.
- [x] AC-02: Valid IDs and generated IDs preserve receipt replay; checks pass.
- [ ] AC-03: Request independent validation and protected publication of the exact head.

## Validation

- A controlled dry-run reproduced receipt traversal outside the receipt root.
- New regression suite initially failed in 21 cases before the correction.
- Focused MCP checks: 36 passed; existing receipt replay remains valid.
- Ruff (including import ordering), diff whitespace and managed governance passed.
- Full governed tests and independent exact-head publication remain in the delivery process.
