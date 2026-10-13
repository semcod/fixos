# Ticket 071: register wellman standard requirements and local CI publication policy

- **ID**: ticket-071
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

Apply the Wellmanifest standards relevant to fixos through the published
tooling instead of hand-written copies:

- `wellman adopt auto` (wellman 0.20.38) registers profiles `baseline` and
  `deployment` with requirements for authority-lifecycle, deployment, docs,
  git-lifecycle, logs, merge, new-project, poa, ticket-lifecycle,
  validation-attestation and worktrees in
  `.governance/standard-requirements.json`, and the default
  `new-project.local-ci-publication/v1` route (`scope.mode: all`).
- `.governance/docs.json` pins `wellmanifest/docs` at its published
  `origin/main` 19efafbeb18923cfd51cc69bd519330488500137 with the
  `docs/standard/policy.json` digest, as other semcod/autogrammar repos do.

This is registration, not a conformance certificate. `wellmanifest/report`
and `wellmanifest/logs` have no released version yet, so no runtime adapter
is adopted for them.

SESSION_EXECUTION_AUTHORIZATION: user requested applying wellmanifest wellman, worktrees, merge, docs, logs, report and other relevant standards to fixos.

## Acceptance criteria

- [x] AC-01: `wellman adopt auto --dry-run` reports no further change and `wellman check` passes.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
