---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "wellmanifest-standards",
  "kind": "information",
  "version": 4,
  "title": "Which Wellmanifest standards fixos applies and how",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-11-18",
  "source_revision": "e648537b2d87000f32333e97693c6b39249481c7",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/fixos/pull/100",
    "https://github.com/semcod/fixos/pull/103",
    "https://github.com/semcod/fixos/pull/196",
    "https://github.com/semcod/fixos/pull/197",
    "https://github.com/semcod/fixos/pull/198",
    "https://github.com/semcod/fixos/pull/199",
    "https://github.com/semcod/fixos/pull/200"
  ]
}
---

# Which Wellmanifest standards fixos applies and how

<!-- docs:section summary -->
## Cel i rezultat

`fixos` is a single Python CLI and stdio MCP package (`2.7.0`). This index records each pinned Wellmanifest standard revision, selected profile, non-applicable packs, and separate static vs runtime verification evidence. Immutable upstream pins live in `.governance/standards-lock.json` and `.governance/standard-adoption.json`.

<!-- docs:section details -->
## Zakres i rozwiązanie

| Standard (revision) | Profile / role | Evidence in fixos |
|---|---|---|
| wellman `0.23.1` | pack & profile runner | `.governance/standard-requirements.json`, `.governance/authority-lifecycle.json` |
| poa `0.1.0` (`b0432f3`) | `minimal-plan/v1` + single-use grant | `.governance/poa.json`, `fixos/poa_grants.py`, `fixos/poa_registry.py` |
| mcp `0.1.0` (`91f0271`) | `registry/v1` + `urn:uuid:` resources + durable receipts | `fixos/mcp_server.py`, `fixos/mcp_resources.py`, `fixos/mcp_receipts.py` |
| nl-uri-dsl-llm `1.5.0` (`adc0056`) | `semantic-v1` (`wellmanifest.nl-plan/v1`) | `.governance/nl-uri-profile.json`, `fixos/nl_router.py` |
| uriprocess `0.3.0` (`0a81334`) | canonical `fixos://` URI identity only | `fixos/poa_registry.py` (no standalone `uriprocess.json` capsule) |
| ssot `91c894b` | propose-only decisions + `standards-lock/v1` | `.governance/standards-lock.json`, [docs/ssot](../ssot/) |
| semver `432b6f9` | host SemVer in `VERSION` + `pyproject.toml` | `tests/unit/test_version_parity.py` |
| reuse `4c7dba2` / nohardcode `922cc51` | docs index + runbook; balanced audit | [TROUBLESHOOTING](../SERVICE/TROUBLESHOOTING.md), `ticket-074` |

- **Evidence tier separation**: (1) declared manifests (`proves_runtime_s5=False`), (2) deterministic static checkers (`wellman check`, `standard_pack_check.py`, capability parity, FastMCP AST hygiene), and (3) observed runtime canary (`fixos/poa_canary.py`) are reported separately; a manifest never proves S5 runtime execution.
- **uriprocess & excluded packs**: `wellmanifest/uriprocess` is published on `main` (`0.3.0@0a81334`, superseding older `bootstrap/uriprocess-standard` prose); `fixos` adopts its canonical action-URI / resource-URN split without shipping a separate `uriprocess.json` artifact bundle. `wellmanifest/nl-api-llm` (multi-protocol HTTP/frontend menu trees) and `FastMCP` are not used or declared.

<!-- docs:section validation -->
## Weryfikacja

- Static conformance: `wellman check --root .` (`0` errors), `wellman check --root . -s wellmanifest/poa -s wellmanifest/mcp -s wellmanifest/nl-uri-dsl-llm -s wellmanifest/ssot -s wellmanifest/uriprocess`, and `python3 .governance/standard_pack_check.py --root .`.
- Runtime canary (CI): `pytest tests/unit/test_wellman_canary.py` executes live stdio MCP `initialize`, `resources/read` over `urn:uuid:` URNs, PL/EN NL negation and abstention guards, ungranted POA mutation rejection, receipt hash verification, and idempotency conflict checks.

<!-- docs:section risks -->
## Ryzyka i następny krok

Direct edits to `.governance/standard-requirements.json` remain fenced by preserved `refs/heads/ticket/110-sync-standard-requirements-backup` until `#174` (`NP-024` backup ancestry disposition) is closed; until then, upstream pins are enforced through `.governance/standards-lock.json` and `tests/unit/test_wellman_canary.py`. `.reuse/redup-receipt.json` stays a CI check artifact rather than a tracked Git file.
