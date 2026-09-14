# Ticket 22: Remove pfix auto-repair from packaging metadata

- **ID**: ticket-022
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-13

## Goal and scope

On 2026-09-13 the user stated that pfix, intended as development-time
auto-repair, overwrites changes and must be removed from projects or
deactivated (SESSION_EXECUTION_AUTHORIZATION). This project declares a
`[tool.pfix]` table with `auto_apply = true` and `auto_install_deps = true` and
a pfix requirement. This integration ticket removes those declarations and,
where a lockfile exists, regenerates it.

Non-goals: no source or test change, no release, and no rewrite of generated
documentation projections.

## Acceptance criteria

- [x] AC-01: No tracked `pyproject.toml` declares a `[tool.pfix]` table or a
  pfix requirement; every other parsed value is unchanged.
- [ ] AC-02: Not in this ticket. `uv.lock` still lists the pfix requirement
  because `.governance/manifest.json` assigns `uv.lock` to no workstream;
  regenerate it after a governance ticket declares lockfile ownership.

Fleet evidence: `subactor/docs/architecture/analysis/semcod-library-quality.md`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
