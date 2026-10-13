# Ticket 069: cleanup reports filesystem-real freed space, not cache-dir size drop (hardlinks)

- **ID**: ticket-069
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

On 2026-10-13 `fixos cleanup -s npm,uv,pnpm,conda,pip,go,cargo --yes` reported
"Zwolniono" 5.62 GB, while `df` showed only ~4.2 GB returned. `uv` (and pnpm,
conda) hardlink cache files into virtualenvs, so deleting the cache link frees
nothing while the environment link survives. `ServiceCleaner.cleanup_service`
now subtracts bytes whose inode is still linked outside the cleaned paths and
reports them separately as `shared_hardlink_gb`. Docker keeps its daemon-based
measurement.

SESSION_EXECUTION_AUTHORIZATION: user requested fixing fixos if it does not work correctly ("napraw fixos jesli nie dziala poprawnie").

## Acceptance criteria

- [x] AC-01: `tests/unit/test_service_cleanup.py` covers shared-inode detection and a cleanup whose hardlinked bytes are not reported as freed.
- [x] AC-02: existing cleanup suites and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
