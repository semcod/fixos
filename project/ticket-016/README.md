# Ticket 016: Raise HITL output limit and recover empty LLM responses

- **ID**: ticket-016
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Make the full HITL analysis request large enough for reasoning-heavy GLM 5.3
responses without changing the smaller limits used by short provider calls.
Configure the preferred OpenRouter GLM 5.3 model for low reasoning effort and
fail over to an explicitly configured fallback model when a provider returns
an empty completion instead of silently showing an empty action menu.

Also normalize a bounded, single-word typo such as `clanup` to a cleanup
planning request. This normalization may only ask the LLM for the existing
structured remediation plan; it must never execute a cleanup command or bypass
the normal selection and confirmation flow.

## Acceptance criteria

- [x] AC-01: The request to raise the limit to 50,000 is recorded as
  `SESSION_EXECUTION_AUTHORIZATION`; work remains inside the declared intent.
- [ ] AC-02: Every full interactive HITL turn requests at most 50,000 output
  tokens, while short provider operations retain their existing limits.
- [ ] AC-03: OpenRouter requests for `z-ai/glm-5.3` explicitly use low
  reasoning effort and exclude reasoning details from the returned content.
- [ ] AC-04: An empty non-streaming completion switches to the next configured
  fallback model; exhaustion raises a visible `LLMError` instead of returning
  an empty string.
- [ ] AC-05: A bounded cleanup typo such as `clanup` becomes an explicit
  cleanup-planning prompt without executing commands or widening authority.
- [ ] AC-06: Focused tests, the full Python suite, Ruff, diff validation and
  the managed governance gate pass before publication through `goal -a`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
