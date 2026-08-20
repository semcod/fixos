# Ticket Changelog (ticket-003)

## [0.1.1] - 2026-08-20

- Passed exact-head CI and repository-scoped Validator App approval, then
  merged PR #4 through the protected autonomous merge path.
- Passed post-merge Python, Docker, build/deploy/dispatch/report checks and
  verified automatic implementation-branch deletion.
- Updated the local FixOS environment to integrated 2.2.47 and closed the
  ticket from merged `main` in this governance-only change.

## [0.1.0] - 2026-08-20

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Bounded the optimizer to repository-backed startup policies with dry-run and
  exact-selection safeguards; Docker objects are never deleted.
- Added cached Compose/bind-mount-to-Git evidence and persistent `docker exec`
  helper correlation.
- Added exact-ID restart-policy updates, opt-in bounded container stopping and
  post-action verification.
- Added deterministic coverage for stale, recent, dirty, missing, ambiguous,
  dry-run, selection and mutation cases.
- Separated the Docker and prior PyCharm ticket worktrees so each has an
  independent governed implementation diff.
- Treated `restarting`, `paused` and other non-terminal container states as
  active for explicit stopping and require `exited` or `dead` verification.
- Exercised a live 3-day optimization: disabled autostart and stopped 13 stale
  services without deleting Docker data, then verified helper-process exit.
- Added an interactive `fixos cleanup --docker-stale-services` flow with a
  3-day default, read-only output modes, exact selection and two mutation
  decisions.
- Advertised stale-service optimization on the FixOS welcome screen and added
  focused CLI routing and safety coverage.
