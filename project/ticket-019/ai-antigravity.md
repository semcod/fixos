---
participant-id: agent:antigravity
participant: antigravity
role: agent
ticket: ticket-019
---
# Participant: antigravity (AI agent)

## Understanding

User requested: "fixos cleanuo to literowka i ltego typu problemy powinny byc wylapywane jako literowki, ponaprawiaj to co jeszce nie dziala poproawnie i polepsz jakosc".
Recorded SESSION_EXECUTION_AUTHORIZATION for this bug fix and quality improvement ticket.
Identified problems:
1. `NaturalLanguageGroup` forwards any unknown command to `ask`, bypassing typo detection and causing unintended LLM execution.
2. `ask_cmd.py` heuristic matching maps `wylacz`/`usun`/`stop` unconditionally to Docker commands regardless of subject.
3. `_execute_with_llm` lacks dangerous command blocking (`is_dangerous`) and lacks confirmation prompts before modifying system state.

## Execution plan

1. Update `NaturalLanguageGroup` in `fixos/cli/shared.py` to detect close typo matches and either prompt the user or raise `NoSuchCommand` with suggestion, and only forward genuine natural language queries to `ask`.
2. Refine heuristic matching in `fixos/cli/ask_cmd.py` to ensure Docker commands require docker context and module routing works properly.
3. Add safety checks (`is_dangerous`, interactive confirmation for state-modifying commands) to `_execute_with_llm` and check verification commands in `ask_cmd.py`.
4. Add comprehensive unit tests in `tests/unit/test_ask_and_nl_group.py`.
5. Run tests and `./project/governance-check.sh`.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Configured intent.json, README.md, and implementation files.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.

