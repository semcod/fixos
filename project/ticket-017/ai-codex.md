---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-017
---
# Participant: codex (AI agent)

## Understanding

The current FixOS implementation removes raw values but also destroys useful
relationships: every foreign home path becomes the same generic placeholder,
IPv4 prefixes remain exposed while endpoint identity is lost, and repeated UUID
values cannot be correlated. Its preview parser also strips alias brackets. Existing
tests verify leak prevention, but encode several of these lossy behaviours and
therefore cannot prove conformance with the context-preserving standard.

The safe compatibility boundary is to keep the current two-value
`anonymize()` result and legacy `[USER]`, `[HOME]` and `[HOSTNAME]` execution
placeholders. New numbered aliases are only reversible through an explicit
memory-only context and an exact allowed-token set. Calls without a context use
an isolated context for that payload, preventing implicit cross-session
linkability.

## Execution plan

1. Record the four-file implementation boundary and baseline regression
   evidence.
2. Add failing contract tests for path structure, stable UUID/IP aliases,
   semantic IP classes, idempotence and fail-closed local resolution.
3. Replace lossy regex masking with parsed, context-aware aliases while keeping
   credentials irreversibly redacted and preserving the legacy API.
4. Route the older `fixos.anonymizer` compatibility module through the shared
   implementation so the LLM shell cannot retain weaker privacy behaviour.
5. Preserve bracketed aliases in the preview and expose the exact payload
   digest, then run focused/full validation and the managed governance gate.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
