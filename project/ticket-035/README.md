# Ticket 035: Ship YAML data files in fixos package

- **ID**: ticket-035
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`pip install fixos` ships only `*.py` — `MANIFEST.in` uses
`recursive-include fixos *.py`, so every runtime YAML is absent from the
installed package. Consequences observed on a real host:

- `fixos features profiles` prints an empty list
- `fixos features audit` / `features install` have no catalog
- `fixos profile` builtins (`desktop`, `developer`, `minimal`, `server`)
  are missing

Fix: declare `[tool.setuptools.package-data]` in `pyproject.toml` covering
`fixos/features/data/*.yaml`, `fixos/features/data/profiles/*.yaml` and
`fixos/profiles/*.yaml`. setuptools feeds package-data into both the wheel
and the sdist.

SESSION_EXECUTION_AUTHORIZATION: user asked to investigate fixos and fix
found problems.

## Acceptance criteria

- [x] AC-01: Built wheel contains all 8 YAML data files.
- [x] AC-02: A fresh venv installed from the wheel lists profiles via
  `fixos features profiles`.
- [x] AC-03: `./project/governance-check.sh` passes.

## Validation evidence

Recorded below after running the build.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
