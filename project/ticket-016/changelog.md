# Ticket Changelog (ticket-016)

## [0.1.0] - 2026-09-01

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Authorized a bounded application change for the full HITL token ceiling,
  GLM reasoning controls, empty-response fallback and cleanup typo intent.

## Implemented

- Raise full interactive LLM turns to a 50,000-token output ceiling without
  changing short-call defaults.
- Send OpenRouter GLM 5.3 requests with low reasoning effort and excluded
  reasoning details.
- Fail over on empty assistant content and surface fallback exhaustion as an
  LLM error instead of an empty action menu.
- Normalize bounded cleanup typos to planning-only prompts with the existing
  selection and confirmation gates intact.
