# Ticket 118: Declare the publication Makefile owner

- **ID**: ticket-118
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-01
- **maxActiveMinutes**: 30

SESSION_EXECUTION_AUTHORIZATION: the user requested execution, tests and protected merges for the cross-repository Goal publication migration. The existing Makefile has no declared workstream owner. Its source must remain unchanged until this exact target-owned configuration is independently merged. The adoption contract marks this manifest extendable; its managed base and every protected managed digest remain unchanged. Existing Goal configuration already requires Goal -a and clean pull-request delivery.

- [x] AC-01: Assign only the existing unowned Makefile to integration; preserve all other ownership and managed content.
- [ ] AC-02: The existing projection regression and actual Goal source delivery pass.
- [ ] AC-03: Required platform checks and independent exact-head/current-base publication pass.

Bounded prerequisite amendment: the existing projection regression detects that project artifact references still point to the previous manifest. Include only the target-owned standard-adoption declaration, as in the published project procedure ticket-092. Rebind artifact references for the exact edited extendable manifest; preserve source revisions, levels, evidence and every standard-managed file/hash. The failed regression is retained as receipt:fixos118/projection-before; source ownership remains fenced through the existing controller.

Validation: the existing adoption-projection regression failed before the project artifact reference rebind and passes afterwards. Exactly one previously unowned path is added; all other manifest values, all source pins/levels/evidence and all 98 standard-managed digests are unchanged. The publication recipe remains untouched until this prerequisite is independently accepted.
