# ticket-172: chore(governance): register stray root path ownership for Windows checkout cleanup

- **ID**: ticket-172
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Register `Since no actual code in/**` under `coordination.workstreams.governance.ownedPaths` in `.governance/manifest.json` and update the corresponding `.governance/manifest.json` artifact SHA-256 digests in `.governance/standard-adoption.json` so a scoped `governance` cleanup ticket can remove the invalid NTFS stray file under `Since no actual code in/` (trailing period in filename) that prevents `git checkout` on Windows.

## Acceptance criteria

- [x] AC-01: `.governance/manifest.json` includes `"Since no actual code in/**"` in `coordination.workstreams.governance.ownedPaths` and `.governance/standard-adoption.json` digests match the updated manifest (`standard_pack_check.py --strict` and `test_standard_adoption_projection.py` pass).
- [x] AC-02: `./project/governance-check.sh` passes with zero errors and warnings.
