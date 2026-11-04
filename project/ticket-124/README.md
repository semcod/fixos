# Ticket 124: Explainable large-file storage triage without LLM

- **ID**: ticket-124
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested richer Fixos storage
diagnosis, files over 500 MB grouped for quick decisions, and explainable
decisions without an LLM. Planfile PLF-039 owns this request. Implement only
the disjoint read-only scanner, deterministic rules, CLI and regressions.
No data deletion or cleanup execution is authorized by this feature request.

The independently published native v5 allocator reserved this canonical
worktree and fresh owner/session-bound lease (rev1/fence1). The old allocator's
unimplemented ticket-123 intake is preserved in ignored recovery. No foreign
lease was reused. Base: 947a1492906605dd79a33132af871d1a6774cc82.

## Acceptance criteria

- [ ] AC-01: Scan files strictly above 500 decimal MB by default, with truthful time/entry bounds and largest-first results across the scanned scope.
- [ ] AC-02: Report logical/allocated sizes, hardlinks, sparse files, owner, age, role, protected/manager/review decisions and reasons without LLM/network access or mutation.
- [ ] AC-03: Probe active swap and open file identities conservatively; group proposals and export JSON, CSV and HTML for human decisions, without fabricated reclaim guarantees.
- [ ] AC-04: Integrate lazy `fixos storage` and retain DiskAnalyzer compatibility; test boundaries, late largest files, permissions, symlinks, hardlinks, protections and no-LLM behavior.
- [ ] AC-05: Run affected regressions, lint and native governance. Canonical docs and further diagnostic improvements use an integration-owned scope; preserve cleanup execution and other writers.

## Tracking boundary

Validation 2026-11-04: 52 affected behavioral/compatibility tests PASS in 0.58s;
managed governance PASS (0 errors/warnings); changed Python files pass Ruff.
The read-only host trial is explicitly partial and does not authorize deleting
the discovered release artifacts. Canonical usage/analysis documentation is
owned separately by integration ticket-125 under PLF-039. No data was deleted.
AC-01 through AC-04 are locally verified; protected publication and the linked
documentation delivery remain separate from those test results.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
