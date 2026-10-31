# Ticket 111: Keep FixOS MCP stdout valid during cleanup

- **ID**: ticket-111
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

Keep stdout exclusively JSON-RPC when FixOS MCP invokes CLI cleanup helpers.
A controlled probe using a mocked cleanup helper emitted a plain progress line
before the response, breaking the MCP stream. Route helper output to stderr,
including failed tool calls, and verify the next request still works.

SESSION_EXECUTION_AUTHORIZATION: The user requested using FixOS through MCP
for host storage diagnosis, repairing FixOS when needed, and merging FixOS
work through its protected delivery process. This ticket covers the bounded
MCP repair and its publication. Preserve active IDEs, volumes and unknown work.

## Acceptance criteria

- [x] AC-01: Successful and failed cleanup calls produce parseable JSON-RPC
  stdout; helper messages go to stderr and a subsequent ping succeeds.
- [x] AC-02: Existing MCP behavior and the managed governance gate pass.
- [ ] AC-03: Request independent validation and publication of the exact head.

## Validation

- Regression reproduced: both success and failure cases rejected non-JSON CLI
  output before the correction (2 failures, 6 passes).
- After correction: `python -m pytest tests/unit/test_mcp_server.py -q` — 8 passed.
- `python -m ruff check --no-cache fixos/mcp_server.py tests/unit/test_mcp_server.py` — passed.
- `./project/governance-check.sh` — passed, no warnings.
- Protected publication remains pending independent exact-head approval.
