# Ticket 005: Show top process load and verify stale Docker services

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-20

## Goal and scope

Make the fast FixOS diagnostic useful below alert thresholds by always showing
up to five processes currently exerting the greatest sampled CPU or memory
pressure, including their stable PID. Verify the existing conservative Docker
startup optimizer against the user's three-day inactivity threshold without
stopping containers that cannot be tied safely to an inactive clean repository.

## Acceptance criteria

- [x] AC-01: Fast resource collection primes and samples per-process CPU over a
  bounded interval and ranks CPU-heavy and memory-heavy processes together.
- [x] AC-02: Human-readable `fixos quick` output always shows up to five top
  processes with PID, CPU and RAM, even when CPU and memory alerts are absent.
- [x] AC-03: A read-only Docker review at the three-day threshold reports safe
  candidates and protection reasons without changing any container.
- [x] AC-04: Focused/full tests, formatting, compilation and governance pass.

## Validation result

- Live `fixos quick --no-save` displayed PyCharm first at 223.4% CPU and 19.9%
  RAM while total CPU was only 34%, proving the list is no longer alert-gated.
- The three-day Docker dry run reviewed 191 containers and 92 IDE-owned
  `docker exec` helpers. It found zero safe candidates and made zero changes.
- The protected containers included repositories active 1.8 days ago, dirty
  repositories, ambiguous mappings and containers with no reliable repository
  mapping.
- Focused tests passed 11/11; the full suite passed with 502 tests, 5 skips and
  16 intentional deselections.

## Publication

- [PR #8](https://github.com/semcod/fixos/pull/8) passed the three-version
  Python suite, five-distribution Docker matrix, summary and remote lifecycle
  checks on exact head `03925dcbd4b3790d2206ef08304e4e7d5f4042e9`.
- Repository-scoped Validator App review `4981345256` approved that exact head
  for `ticket-005` after two stable policy reads.
- The protected validator merged PR #8 as
  `715f9611ab02c0808c7c5b74ed92d8eafb84086a`; the remote implementation branch
  was deleted automatically.
- Post-merge runs `32355746239` and `32355746264` passed the Python and complete
  five-distribution Docker suites, including `test-summary`, on integrated
  `main`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
