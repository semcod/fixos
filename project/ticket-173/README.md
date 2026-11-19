# ticket-173: fix(governance): remove invalid NTFS stray path breaking Windows checkout

- **ID**: ticket-173
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

1. Match the trailing-space directory name via `Since no actual code in*/**` in `.governance/manifest.json` (synchronizing `.governance/standard-adoption.json`), remove the accidentally committed LLM-output artifact whose trailing space and trailing period cause `git checkout` / `actions/checkout@v4` to fail on Windows NTFS (`invalid path`, exit code 128), and ignore `/Since no actual code in*/` in `.gitignore` to prevent recurrence.
2. Route `archive.ubuntu.com` and `security.ubuntu.com` to the Fastly-backed `mirrors.edge.kernel.org` mirror in `.github/workflows/multi-system-tests.yml` (`test-ubuntu`) to eliminate Canonical `:80` connection timeouts on GitHub Actions runners.

## Acceptance criteria

- [x] AC-01: No tracked files remain under `Since no actual code in*/**`, `.governance/standard-adoption.json` matches `.governance/manifest.json`, and `/Since no actual code in*/` is ignored in `.gitignore`, allowing native Windows `git checkout` to execute cleanly.
- [x] AC-02: `test-ubuntu` in `.github/workflows/multi-system-tests.yml` uses `mirrors.edge.kernel.org` and `./project/governance-check.sh` passes with zero errors and warnings.
