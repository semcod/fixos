# Ticket 153: MCP URN resources endpoints and shared NL-to-URI router with negation and abstention

- **ID**: ticket-153
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#165` / `PLF-21816` and `#167` / `PLF-21818`).

## Goal and scope

1. Advertise `resources` in MCP `initialize` and implement `resources/list` (with
   cursor pagination), `resources/templates/list`, and `resources/read` in
   `fixos/mcp_resources.py` for registry catalog, quick snapshot, POA plans, and
   execution receipts addressed via standard `urn:uuid:<uuid>` URNs (`Closes #165`).
2. Unify natural-language routing across `ask`/shell/MCP on `wellmanifest.nl-plan/v1`
   (`semantic-v1`) in `fixos/nl_router.py` with PL/EN diacritic normalization,
   negation handling (`nie usuwaj`), inquiry/ambiguous/unknown abstention
   (`clarify` / `unsupported`), standalone `auto` guard, and validated optional
   LLM DSL output (`Closes #167`).
3. Harden `mcp_receipts.py` and `poa_grants.py` (parent-directory `fsync`,
   `validated_request_id` entry containment, and exact ECMA-262 / RFC 8785 float
   formatting) and remove the unsupported `optional FastMCP` docstring claim.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_mcp_resources.py -q` verifies pagination,
      read-only URN reads, retention/scope/action-URI rejections, and clean stdout.
- [x] AC-02: `pytest tests/unit/test_nl_router.py tests/unit/test_ask_and_nl_group.py -q`
      verifies PL/EN diacritics, negation, inquiry abstention, standalone `auto`,
      and `ask` CLI integration.
- [x] AC-03: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
