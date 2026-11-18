# ticket-162: fix(governance): reconcile standard-adoption.json after 0.20.162 upgrade

- **ID**: ticket-162
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Reconcile repository-owned `.governance/standard-adoption.json` after `PR #207` (`229fabd4`, `new-project 0.20.162`) reset `.governance/manifest.json` projection digests (`STD-ADOPTION-DRIFT`), lowered four `baseline` S4 packs to `S3` (`STD-PACK-LEVEL`), and omitted `wellmanifest/docs` (`STD-PACK-MISSING`), breaking `tests/unit/test_standard_adoption_projection.py`.

## Acceptance criteria

- [x] AC-01: `.governance/standard-adoption.json` updates `.governance/manifest.json` SHA-256 (`55716d09d803921a5afd7230adc0f6c5dfdff9972606cbe8d2fcd58241d1a102`), restores `mode: "enforce"` and `S4` external proof on `wellmanifest/{new-project,git-lifecycle,merge,validation-attestation}`, and records `wellmanifest/docs` (`0.6.0@b536d01`) at `S2`.
- [x] AC-02: `python3 .governance/standard_pack_check.py --root . --strict --format json`, `pytest -q tests/unit/test_standard_adoption_projection.py`, and `./project/governance-check.sh` pass with 0 findings.

## Evidence

- Verified `standard_pack_check.py --strict` (`ok: true`, `findings: []`), `test_standard_adoption_projection.py` (`1 passed`), and `./project/governance-check.sh` (`GOV-PASS`).
