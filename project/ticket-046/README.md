# Ticket 046: adopt wellmanifest/new-project 0.20.32

- **ID**: ticket-046
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-18

## Goal and scope

Upgrade the pinned standard-managed governance projection from
`wellmanifest/new-project` 0.20.31 (`2b016654cff1a1ccef2c0d6126a9c2550ae6b37a`)
to 0.20.32 (`b6ba9c21a65a6a5648ecf904b64c3b75295e136f`) using the immutable
adoption/updater `create_adoption_lock.py --upgrade`, and declare the adopted
standard in `pyproject.toml` `[tool.wellmanifest]`.

## Delivery

- `create_adoption_lock.py --check` reported 17 managed-file drifts; `--upgrade`
  applied exactly those 17 updates (`.aider.conf.yml`,
  `.cursor/rules/new-project-standard.mdc`, `.github/copilot-instructions.md`,
  `.governance/*`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `scripts/install-agent-hosts.sh`, `.governance/manifest.lock.json`).
- `pyproject.toml`: `standard = "0.20.32"`, `revision = "b6ba9c2…"`.

## Acceptance criteria

- [x] AC-01: Scope is approved by a human owner. (SESSION_EXECUTION_AUTHORIZATION: user requested execution of all tickets autonomously.)
- [x] AC-02: `./project/governance-check.sh` passes; `python -m pytest -q` stays green.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
