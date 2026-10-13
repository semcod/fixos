---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "wellmanifest-standards",
  "kind": "information",
  "version": 2,
  "title": "Which Wellmanifest standards fixos applies and how",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-10-13",
  "source_revision": "0890e5325513b2c49a4a7a0eaf73737e04ab7349",
  "priority": "P2",
  "evidence": ["https://github.com/semcod/fixos/pull/100", "https://github.com/semcod/fixos/pull/103"]
}
---

# Which Wellmanifest standards fixos applies and how

<!-- docs:section summary -->
## Cel i rezultat

fixos is one Python CLI package. This page records, per standard, the pinned
revision, what applies here and the evidence, so an adopter does not have to
re-derive it. Registration lives in `.governance/standard-requirements.json`
(`wellman adopt auto`); this page is the human index.

<!-- docs:section details -->
## Zakres i rozwiązanie

| Standard (revision) | Applies as | Evidence in fixos |
|---|---|---|
| wellman 0.20.38 | registry + `wellman check` | `.governance/standard-requirements.json` |
| ssot `91c894b` | two propose-only decisions | [docs/ssot](../ssot/) version, ollama-endpoint |
| nohardcode `922cc51` | balanced audit; fix real defects first | ticket-074 (NOHARDCODE-006) |
| reuse `4c7dba2` | docs index + runbook; scan receipt open | [TROUBLESHOOTING](../SERVICE/TROUBLESHOOTING.md) |
| semver `432b6f9` | host package only: SemVer in `VERSION` | `tests/unit/test_version_parity.py` |
| uriprocess `fa7b715` | not applicable | fixos ships no URI process package |

- **ssot**: `VERSION` is canonical; `pyproject.toml` must stay identical
  (parity test) and `setup.py` reads `VERSION`. The default Ollama
  address comes only from `OLLAMA_HOST` via `fixos.config.ollama_host_url()`
  (LLM provider and model cleanup); `OLLAMA_BASE_URL` is an explicit,
  LLM-only override layered on top.
- **nohardcode** (2026-10-13 audit, 195 findings): 145 are NOHARDCODE-007
  `print()` in interactive CLI modules, which is terminal UI, not logging;
  33 NOHARDCODE-001 lists are CLI choices and service tables. Real defects are
  fixed per ticket; the rest needs a repo policy before it can gate CI.
- **semver**: rules SEMVER-002 and 012–016 address firmware images and OTA;
  fixos has none. Releases bump `VERSION` (patch for fixes) through a ticket
  and publish after merge with `goal -a --delivery-mode publish-only`.
- **uriprocess** is published only on `bootstrap/uriprocess-standard`; no
  fixos component is distributed as a URI process package.

<!-- docs:section validation -->
## Weryfikacja

`wellman check --root .`; `PYTHONPATH=src python3 -m ssot validate
docs/ssot/<id>.ssot.json` (in wellmanifest/ssot); `python3
standard/conformance.py --project <fixos>` (wellmanifest/reuse) reports
REUSE-004 and REUSE-006A passing; REUSE-006B only finds \`docs/TROUBLESHOOTING.md\`
or \`errors/*.md\`, which conflicts with the docs location rule, and REUSE-002
is unverified.

<!-- docs:section risks -->
## Ryzyka i następny krok

REUSE-002 needs a revision- and digest-bound `.reuse/redup-receipt.json`;
`.reuse/` is not owned by any workstream yet. nohardcode becomes a CI gate
only after a reviewed `nohardcode-policy.json` baseline.
