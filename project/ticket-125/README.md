# Ticket 125: Document deterministic storage triage and diagnostic improvement findings

- **ID**: ticket-125
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Planfile PLF-039 and the user's request to
develop offline storage diagnosis include canonical usage documentation and
an analysis of further improvements. Own only the three declared documentation
paths. Source implementation belongs to disjoint application ticket-124,
commit cfeea5b8060082350c185b00e300641a46cc64b3. This writer owns canonical
worktree ticket-125--storage-triage-docs and fresh allocation lease rev1/fence1.
Do not change source, cleanup behavior, package version or other tickets.

## Acceptance criteria

- [ ] AC-01: Document exact CLI usage, units, decisions, report formats, no-LLM behavior and uncertainty at docs/information/storage-triage.md.
- [ ] AC-02: Publish an evidence-bound analysis of implemented fixes, limits and prioritized next improvements at docs/analysis/storage-diagnostics.md.
- [ ] AC-03: Index both documents, validate metadata/sections/links and native governance; keep code, publication and deployment states distinct.

## Tracking boundary

Validation: metadata, required v1 sections, index links, exact source objects
and local document links PASS. Native governance PASS (0 errors/warnings).
Application source is pushed in PR156; these documents do not claim merge or
runtime deployment. Raw host inventory is not part of the source delivery.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
