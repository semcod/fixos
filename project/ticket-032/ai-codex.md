# Agent record — ticket-032

## Authorization

The user explicitly requested `kontynuuj` and `wykonaj`; this is recorded as
`SESSION_EXECUTION_AUTHORIZATION` for the bounded ticket scope. No authority
is granted to run package cleanup on the host, access secrets, or bypass the
OneDev/Validator delivery path.

## Plan

- Make broad package-removal commands an explicit fail-closed case in the
  natural-language and structured HITL paths.
- Replace wildcard and shell-substitution package removal suggestions from
  the storage analyzer with exact, quoted package names observed by the
  read-only scan.
- Update the package-analysis prompt and add regression tests for exact target
  inventory, dry-run behavior, confirmation boundaries, and secret-free
  output.

## Progress

Ticket initialized from PLF-003 / GitHub Issue #47. Implementation and
validation evidence will be appended here as the work proceeds.

## Implementation review

- Added a single package-cleanup guard to structured remediation parsing, the
  LLM `ask` path and the final HITL execution boundary.
- Replaced DNF wildcard/command-substitution suggestions with bounded,
  shell-quoted package names observed by read-only diagnostics.
- Kept host cleanup out of this ticket; tests mock command output and verify
  the generated plan.

SESSION_EXECUTION_AUTHORIZATION: `kontynuuj, wykonaj, testuj, scalaj`.

## Validation evidence

- Focused package/ask/core/storage suite: `100 passed`.
- Full suite: `631 passed, 5 skipped, 16 deselected`.
- `./project/governance-check.sh --base origin/main --head HEAD --actor agent`:
  `GOV-PASS`.
- `python -m compileall -q fixos tests`, targeted `ruff check` and `git diff
  --check`: passed.
- No package cleanup command was run on the host; all package output is mocked
  in tests and exact-target generation is bounded to the read-only inventory.
