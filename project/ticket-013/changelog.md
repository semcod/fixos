# Ticket Changelog (ticket-013)

## [0.1.0] - 2026-09-01

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Scoped a regression fix that makes the timeout per LLM turn while preserving
  wall-clock session reporting and all command safety boundaries.
- Refreshed the timeout before each LLM call, recalculated menu time after the
  response and clarified the terminal label for the per-turn limit.
- Added regression tests for the slow-diagnosis selection path and total
  wall-clock summary reporting.
