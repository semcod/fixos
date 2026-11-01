# Ticket 119: Reuse Goal for publication and repair supported build tooling

- **ID**: ticket-119
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-01
- **maxActiveMinutes**: 45

SESSION_EXECUTION_AUTHORIZATION: execute, test and request protected merges and publication for the authorized Goal publication migration. The independently merged ticket-118 assigns the existing Makefile to integration. An isolated unchanged-source build proves setuptools 68 rejects the existing SPDX license; 77.0.3 succeeds. Existing lock root and Goal tooling are stale. Preserve Python 3.10+ runtime support and all mandatory runtime requirements.

- [x] AC-01: make publish delegates directly to Goal with exact cwd/argv and failure propagation, with no prior build/clean/upload.
- [x] AC-02: supported backend and Goal publish tooling, aligned version projections, scoped tests and actual Goal source delivery pass.
- [ ] AC-03: required checks and independent merge pass; publish the material fix through Goal and verify registry artifacts.
