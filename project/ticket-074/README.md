# Ticket 074: single Ollama endpoint from OLLAMA_HOST for LLM config and cleanup

- **ID**: ticket-074
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

`wellmanifest/nohardcode` (0.2.0-dev, balanced) on fixos reported
NOHARDCODE-006 for `http://localhost:11434/v1` in `config.py` and
`127.0.0.1:11434` in `service_cleanup.py`, and NOHARDCODE-009 for
`/home/user` in `cleanup_planner.py`. The two Ollama literals were also a real
SSOT defect: `fixos token`/`provider` tell users to set `OLLAMA_HOST`, model
cleanup honoured it, but the LLM provider ignored it and always used localhost.

`fixos.config.ollama_host_url()` is now the single source (OLLAMA_HOST, then
`127.0.0.1:11434`); the LLM provider derives `<host>/v1` from it unless
`OLLAMA_BASE_URL` is set, and `ServiceCleaner._ollama_base_url` delegates to
it.

The NOHARDCODE-009 hit is sample data inside the demo `main()` of
`cleanup_planner.py`; touching that file makes CI lint its 47 pre-existing
ruff findings, so it is left for a separate lint ticket.

SESSION_EXECUTION_AUTHORIZATION: user requested implementing wellmanifest ssot, nohardcode and reuse in fixos.

## Acceptance criteria

- [x] AC-01: tests cover URL normalisation, shared endpoint for LLM and cleanup, and OLLAMA_BASE_URL precedence.
- [x] AC-02: full suite and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
