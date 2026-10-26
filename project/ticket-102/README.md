# Ticket 102: Avoid unconditional LLMClient initialization in AutonomousSession and FixOrchestrator when LLM is disabled (#129)

- **ID**: ticket-102
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Fix semcod/fixos#129 (PLF-038). When `fixos auto` (which defaults to `--no-llm`)
or `fixos fix --mode autonomous` runs without `GEMINI_API_KEY`, `FixOsConfig.load()`
defaults `gemini_transport` to `"native"`. `AutonomousSession.__init__` and
`FixOrchestrator.__init__` unconditionally instantiated `LLMClient(config)`, which
instantiates `GeminiNativeClient(config)` and immediately raises
`LLMError("Brak klucza API dla Gemini – ustaw GEMINI_API_KEY")` before
`_is_llm_active()` is consulted. Guard `LLMClient` creation in both constructors
so LLM-free heuristic mode (`use_llm=False` or missing API key when `use_llm=None`)
never fails during session initialization.

## Acceptance criteria

- [x] AC-01: `AutonomousSession` and `FixOrchestrator` do not instantiate `LLMClient` when `use_llm=False`, and fall back to `self.llm = None` when `use_llm is None` and `LLMClient(config)` raises `LLMError`.
- [x] AC-02: End-to-end `fixos auto --dry-run` and unit tests in `tests/unit/test_auto_no_llm.py` pass with `gemini_transport="native"` and no API key.

## Execution authorization

SESSION_EXECUTION_AUTHORIZATION recorded from user instruction to create a ticket
in `semcod/fixos` and fix `LLMClient` initialization in `AutonomousSession` and
`FixOrchestrator` for `fixos auto` (`PLF-038` / `semcod/fixos#129`).
