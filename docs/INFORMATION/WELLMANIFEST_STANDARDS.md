---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "wellmanifest-standards",
  "kind": "information",
  "version": 5,
  "title": "Which Wellmanifest standards fixos applies and how",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-11-18",
  "source_revision": "f989c7103ae2d3870639d9bfb4fc18a1e4d29605",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/fixos/pull/100",
    "https://github.com/semcod/fixos/pull/103",
    "https://github.com/semcod/fixos/pull/196",
    "https://github.com/semcod/fixos/pull/197",
    "https://github.com/semcod/fixos/pull/198",
    "https://github.com/semcod/fixos/pull/199",
    "https://github.com/semcod/fixos/pull/200",
    "https://github.com/semcod/fixos/pull/203"
  ]
}
---

# Which Wellmanifest standards fixos applies and how

<!-- docs:section summary -->
## Cel i rezultat

`fixos` is a single Python CLI and stdio MCP package (`2.7.1`). This index records each pinned Wellmanifest standard revision, selected profile, applicability classification (`PLF-033`), and separate static vs runtime verification evidence. Immutable upstream pins and SHA-256 digests live in `.governance/standards-lock.json` and `.governance/standard-adoption.json`.

<!-- docs:section details -->
## Zakres i rozwiązanie

| Standard (revision) | Profile / applicability | Evidence in fixos |
|---|---|---|
| wellman `0.23.1` | pack & profile runner | `.governance/standard-requirements.json`, `.governance/authority-lifecycle.json` |
| poa `0.1.0` (`b0432f3`) | `minimal-plan/v1` + single-use grant | `.governance/poa.json`, `fixos/poa_grants.py`, `fixos/poa_registry.py` |
| mcp `0.1.0` (`91f0271`) | `registry/v1` + `urn:uuid:` resources + durable receipts | `fixos/mcp_server.py`, `fixos/mcp_resources.py`, `fixos/mcp_receipts.py` |
| nl-uri-dsl-llm `1.5.0` (`adc0056`) | `semantic-v1` (`wellmanifest.nl-plan/v1`) | `.governance/nl-uri-profile.json`, `fixos/nl_router.py` |
| uriprocess `0.3.0` (`0a81334`) | canonical `fixos://` URI identity only | `fixos/poa_registry.py` (no standalone `uriprocess.json` capsule) |
| docs `0.6.0` (`b536d01`) | `document/v2` + `check.py --prepare` (`policy_sha256: fac05e7...`) | `.governance/docs.json`, `docs/README.md`, `docs/ANALYSIS/`, `docs/INFORMATION/` |
| logs `0.5.0` (`b5c8790`) | `logs.contract.v0.5` JSONL receipt & audit integrity | `fixos/mcp_receipts.py` (`fsync` JSONL/receipts), `errors/` boundary |
| worktrees `0.5.4` (`3146119`) | v5 `.worktrees/ticket-NNN--desc` + relative paths + leases | `.gitignore`, `.subactor/leases/`, host `conformance.py` (`44f1686`) |
| license `1.0.0` (`313ab4a`) | SPDX `Apache-2.0` verified; no automatic relicensing | `LICENSE`, `pyproject.toml`, `.governance/standards-lock.json` |
| report `0.1.0` (`370f532`) | N/A standalone emitter; analysis reports use `docs` v2 | `docs/ANALYSIS/PLANFILE_GITHUB_SYNC_AUDIT.md`, `.governance/standards-lock.json` |
| ssot `91c894b` / semver `432b6f9` | `standards-lock/v1` + SemVer parity | `.governance/standards-lock.json`, `tests/unit/test_version_parity.py` |
| reuse `4c7dba2` / nohardcode `922cc51` | docs index + runbook; balanced audit | [TROUBLESHOOTING](../SERVICE/TROUBLESHOOTING.md), `ticket-074` |

- **Evidence tier separation & scope exclusions**: Declared manifests (`proves_runtime_s5=False`), static checkers (`wellman check`, `standard_pack_check.py`), and observed runtime canary (`fixos/poa_canary.py`) are reported separately. `wellmanifest/nl-api-llm`, `FastMCP`, and Diagit-to-Planfile ticket creation adapters (owned upstream outside `semcod/fixos`) are not declared here.

<!-- docs:section validation -->
## Weryfikacja

- Static conformance: `wellman check --root .` (`0` errors), `python3 .governance/standard_pack_check.py --root .`, and `wellmanifest/docs/docs/standard/check.py` (`0` deliverable findings).
- Runtime canary (CI): `pytest tests/unit/test_wellman_canary.py tests/unit/test_planfile_sprint_contract.py` verifies live stdio MCP `initialize`, `urn:uuid:` `resources/read`, PL/EN NL negation/abstention guards, POA grant enforcement, receipt hashes, and sprint CAS persistence.

<!-- docs:section risks -->
## Ryzyka i następny krok

Direct edits to `.governance/standard-requirements.json` remain fenced by preserved `refs/heads/ticket/110-sync-standard-requirements-backup` until `#174` (`NP-028` / `#575`) is closed; upstream pins are enforced via `.governance/standards-lock.json`.
