# Ticket 132: Correct backup disposition and full archive evidence

- **ID**: ticket-132
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: continue PLF-21812 under "kontynuuj,scalaj".
PR173 was externally merged as5ccc2a9 by the human account, with no observed
reviews. Its worktree was removed with the pending factual correction. Recover
only that saved material document into this separately allocated follow-up;
never reuse the terminal identity or infer independent approval for PR173.
Clarify that publishing analysis does not make backup1e4d4d3 an ancestor of
main, document full verified preservation, and retain the pending exact
disposition and standard dependency. Keep foreign primary changes intact.

## Acceptance criteria

- [x] AC-01: Analysis separates published content, unique history, point-in-time observation and exact cleanup authority; full archive and original candidate are recoverable and no product/configuration bytes change.
- [ ] AC-02: Managed governance and exact-head CI pass, followed by actual independent Validator approval and merge.

## Result

The full archive has952 entries and verified restored bytes. The original
candidate e77f855 is retained in a private incremental bundle, restored and
checked against the prior history bundle. Raw data stay in ignored private
recovery. Local and protected publication checks remain required; no data,
lease or backup-ref cleanup is part of this delivery.
