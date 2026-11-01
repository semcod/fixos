# Ticket 120: Declare the existing Goal publisher for periodic release observation

- **ID**: ticket-120
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-01
- **maxActiveMinutes**: 30

SESSION_EXECUTION_AUTHORIZATION: execute, test and request protected merge for the authorized Goal publication migration and cyclic Heyasa observation. Fixos 2.2.58 is independently merged and publicly verified, but the observer skips the primary as publishing_not_configured because the historical publisher configuration has no publishing.enabled. Add that explicit existing-PyPI opt-in only. No source package, version, runtime requirement, service schedule or registry effect changes. A temporary external configuration already proves the observer recognizes the exact published release.

- [ ] AC-01: Declare only publishing.enabled=true and publishing.registries=[pypi]; the published observer recognizes the exact existing release.
- [ ] AC-02: Existing governance/adoption regression and actual Goal -a source delivery pass.
- [ ] AC-03: Required checks and independent merge pass; canonical primary observer recognizes the public release and retains explicit unknown for unsupported source layout.

The qualified public observer recognizes package/version/artifact hashes after opt-in, but full source verification reports unsupported_source_layout: the current setuptools find configuration has no explicit include list. The public wheel also contains a developer script outside fixos/. This separate material packaging defect belongs to an integration follow-up; this configuration ticket preserves the typed unknown and never claims full source verification.
