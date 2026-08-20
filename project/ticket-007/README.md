# Ticket 007: Harden orphan cleanup process selection

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-20

## Goal and scope

Prevent orphan-workload cleanup from offering containerized processes as
independent host-process targets, and make the Flatpak cleanup selector honor
the documented `critical` priority instead of selecting every recommendation.
Both protections must be revalidated without changing the existing explicit
selection and confirmation model.

## Acceptance criteria

- [x] AC-01: Processes whose cgroup proves Docker, Podman/libpod, containerd or
  Kubernetes membership are reported as protected and never appear in host
  process candidates.
- [x] AC-02: Exact process cleanup performs the same container-membership check
  again before sending a signal.
- [x] AC-03: `_parse_selection("critical", ...)` selects only entries whose
  supplied priority is `critical` and fails closed when priorities are absent.
- [x] AC-04: The Flatpak interactive flow supplies recommendation priorities to
  the shared selector without changing numeric, `all` or `none` behavior.
- [x] AC-05: Deterministic regression tests cover systemd Docker cgroups,
  Kubernetes/libpod forms, apply-time revalidation and mixed priorities.
- [x] AC-06: Focused, full, lint, compile and governance validation pass before
  publication.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
