# Ticket Changelog (ticket-019)

## [0.1.0] - 2026-09-12

- Intercept CLI typos (e.g. `cleanuo` -> `cleanup`) in `NaturalLanguageGroup` using fuzzy matching with interactive confirmation and clean `NoSuchCommand` errors.
- Prevent non-natural-language gibberish from routing to `ask` or LLM.
- Refine heuristic matching in `ask_cmd.py` to ensure Docker commands require explicit docker context and module-specific repairs route properly.
- Add execution safety guards in `_execute_with_llm` and verification (`is_dangerous`, interactive confirmation for system-modifying commands, non-interactive blocking).
- Add unit test suite in `tests/unit/test_ask_and_nl_group.py`.
- Add interactive shell (REPL) and quick menu with TAB completion and command history in `fixos/cli/shell_cmd.py`.
- Publish exact head `2d1faa5...` through PR #37 after all CI and Docker checks passed.
- Merge PR #37 as `f0a3d1c...` and delete remote ticket branch `ticket-019`.
- Close integrated ticket as `DONE / DONE` on default branch.

