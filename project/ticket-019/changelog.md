# Ticket Changelog (ticket-019)

## [0.1.0] - 2026-09-12

- Intercept CLI typos (e.g. `cleanuo` -> `cleanup`) in `NaturalLanguageGroup` using fuzzy matching with interactive confirmation and clean `NoSuchCommand` errors.
- Prevent non-natural-language gibberish from routing to `ask` or LLM.
- Refine heuristic matching in `ask_cmd.py` to ensure Docker commands require explicit docker context and module-specific repairs route properly.
- Add execution safety guards in `_execute_with_llm` and verification (`is_dangerous`, interactive confirmation for system-modifying commands, non-interactive blocking).
- Add unit test suite in `tests/unit/test_ask_and_nl_group.py`.

