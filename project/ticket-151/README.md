# Ticket 151: Canonical POA and MCP registry of commands, URI processes, and URN resources

- **ID**: ticket-151
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#164` / `PLF-21815`) and live verification.

## Goal and scope

Establish a single canonical POA/MCP capability registry in `fixos/poa_registry.py`
covering all public Click commands/subcommands, builtin `PluginRegistry`
diagnostic plugins, and internal MCP operations (`Closes #164`):

1. Inventory every public Click command, Click group subcommand, builtin plugin,
   and internal MCP operation; require either a canonical operation entry or an
   explicit `NonExposedCapability` justification.
2. Separate stable `operation_id` (`^[a-z][a-z0-9_-]{0,63}$`), canonical
   `process_uri` (`fixos://...`), and deterministic UUIDv5 `resource_urn`
   (`urn:uuid:...`); project CLI (`fixos mcp --catalog` / `--registry-v1`) and
   MCP discovery/tool surfaces from the canonical contract.
3. Populate `owner`, `effect`, `inputSchema`, `outputSchema`, `available` +
   availability reason (`unavailableReason`), `deploymentRevision`, and
   `expiresAt` TTL; validate uniqueness and freshness fail-closed.
4. Provide strict `wellmanifest.mcp/registry/v1` export (`export_mcp_registry_v1`)
   alongside consumer-compatible `registry_search()` aliases, and enforce parity
   via `verify_capability_parity()` unit tests.

## Acceptance criteria

- [x] AC-01: `verify_capability_parity()` passes on live `cli` + `PluginRegistry`
      and fails when an unregistered Click command, subcommand, or plugin is added.
- [x] AC-02: `export_mcp_registry_v1()` conforms strictly to
      `wellmanifest.mcp/registry/v1` (`additionalProperties: false`, uniqueness,
      freshness expiry validation).
- [x] AC-03: Existing and new MCP unit tests and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
