# Ticket 017: Adopt context-preserving anonymization

- **ID**: ticket-017
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-01

## Goal and scope

Adopt the context-preserving privacy rules defined by the local
`wellmanifest/anonym` reference without adding a runtime dependency. Improve
FixOS anonymization so distinct identities remain distinguishable to the LLM
through stable, opaque aliases while raw paths, network addresses and hardware
identifiers stay on the trusted side.

Keep the existing `anonymize()` tuple result and legacy primary placeholders so
current HITL, autonomous and shell callers remain compatible. Add an explicit,
memory-only mapping context for callers that need stable aliases across more
than one payload, and require selected-token authorization when resolving those
aliases locally.

## Acceptance criteria

- [x] AC-01: The request to continue and expand the implementation is recorded
  as `SESSION_EXECUTION_AUTHORIZATION`; no provider call or system remediation
  is performed by the work.
- [x] AC-02: Home paths retain their non-sensitive suffix and distinguish the
  primary user from stable foreign-user aliases without leaking usernames.
- [x] AC-03: IPv4 values are parsed and classified as semantic or stable opaque
  aliases; invalid IPv4-like text is not misleadingly transformed.
- [x] AC-04: Repeated UUID identities receive stable aliases inside an explicit
  mapping context, while MAC, serial and credential values remain irreversibly
  redacted and already anonymized values remain idempotent.
- [x] AC-05: The local reverse map is never included in reports or transport
  data, and contextual resolution rejects unknown, semantic and unselected
  aliases while legacy primary placeholders keep working.
- [x] AC-06: The user preview keeps alias brackets visible and binds the shown
  representation to a SHA-256 digest of the exact anonymized payload.
- [x] AC-07: Focused regression tests, the complete Python suite, Ruff, diff
  validation and the managed governance gate pass before publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
