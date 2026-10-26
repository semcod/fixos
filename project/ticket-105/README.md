# Ticket 105: Add MCP server interface for fixos diagnostics and cleanup

- **ID**: ticket-105
- **Owner**: agent:agy
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Add a Model Context Protocol (`wellmanifest/mcp` and `wellmanifest/nl-dsl-llm`) JSON-RPC 2.0 stdio server (`fixos/mcp_server.py`) and CLI command (`fixos mcp` in `fixos/cli/mcp_cmd.py` and `fixos/cli/main.py`) exposing canonical URI operations (`fixos://diagnostics/quick`, `fixos://diagnostics/disk`, `fixos://diagnostics/projects`, `fixos://cleanup/auto`), `registry_search`, `task_plan`, `task_execute`, and `task_status` with durable execution receipts and unit tests (`tests/unit/test_mcp_server.py`).

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner.
- [x] AC-02: `fixos mcp` exposes MCP JSON-RPC 2.0 stdio tools and `--list-tools`, `--plan`, and `--status` modes with unit tests.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
