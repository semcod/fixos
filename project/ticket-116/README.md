# Ticket 116: Avoid repeated ancestor walks in project containment checks

- **ID**: ticket-116
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

Project inventory repeatedly compares every visible process path and mount
against project/artifact paths. The old containment helper constructs and
compares every ancestor each time. Live MCP inventory exceeded 90 seconds;
a diagnostic equivalent-prefix comparison completed the project phase in
9.3 seconds and state inventory in 20.2 seconds. Preserve lexical and native
case behavior while eliminating the repeated ancestor walk.

SESSION_EXECUTION_AUTHORIZATION: the user requested execution of the remaining
FixOS/host repairs on 2026-10-31. This bounded fix includes independent protected
publication and deployment to both existing host installations.

## Acceptance criteria

- [x] AC-01: Equality, descendants, sibling boundaries, relative anchors,
  lexical parent segments and native-case semantics match existing behavior.
- [x] AC-02: Unrelated deep paths do not enumerate their ancestors; affected
  tests and managed governance pass with unchanged cleanup protections.
- [ ] AC-03: Required full checks, independent exact-head publication and
  installed-module/MCP inventory verification succeed.

## Validation

The new ancestor-walk regression failed before the change. After the change,
56 affected tests pass, including all 14 containment tests. The affected
Testless coverage scan also passes all 56 tests. Ruff passes for both changed
implementation paths. Required full checks and independent publication bind
the final commit; live deployment will verify both installed module hashes
and the actual MCP project-inventory duration.
