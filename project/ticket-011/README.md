# Ticket 011: Standaryzowana remediacja wykrytych problemów systemowych

- **ID**: ticket-011
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Replace the flat, regex-only list of LLM commands in the HITL diagnostic session
with a bounded remediation plan tied to detected findings. Each finding can
offer multiple concrete strategies, and each strategy can contain an ordered
command set plus read-only verification. Apply the `wellmanifest/logs` v0.3
separation of ERROR (observed fact), target-owned strategy, policy-filtered
execution and verification without treating an LLM response or diagnostic as
execution authority.

## Acceptance criteria

- [x] AC-01: A structured, closed `fixos.remediation-plan/v1` block binds every
  action to a stable finding reference, severity, standard category, risk and
  verification command; malformed plans fail safely to the legacy parser.
- [x] AC-02: The action menu groups multiple numbered strategies by finding and
  renders ordered command sets, risk, recommendation and verification.
- [x] AC-03: Selecting an action executes its ordered steps with the existing
  safety checks and confirmation boundary, stops on failure or skip and then
  offers its read-only verification steps.
- [x] AC-04: `A` executes no more than one recommended strategy per finding;
  it never executes mutually exclusive alternatives as one aggregate cleanup.
- [x] AC-05: Execution feedback preserves finding/action correlation and uses
  `PLAN`/`APPLY` plus bounded outcomes without logging secrets or claiming that
  a proposed plan grants authority.
- [x] AC-06: Focused tests, the full Python checks and managed governance check
  pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
