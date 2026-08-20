# Ticket 005: Show top process load and verify stale Docker services

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
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

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
