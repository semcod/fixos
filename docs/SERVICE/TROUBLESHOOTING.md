---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "troubleshooting",
  "kind": "service",
  "version": 1,
  "title": "fixos runbook for slow scans, unknown Docker size and freed-space gaps",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-10-13",
  "source_revision": "3cb62dd0c932ca67c07e03ff0a0ec4c86448d193",
  "priority": "P2",
  "evidence": ["https://github.com/semcod/fixos/pull/99", "https://github.com/semcod/fixos/pull/102", "https://github.com/semcod/fixos/pull/103"]
}
---

# fixos runbook for slow scans, unknown Docker size and freed-space gaps

<!-- docs:section summary -->
## Cel i rezultat

Symptoms seen on a loaded host on 2026-10-13, each with its cause and the
command to run. Use it before filing a bug.

<!-- docs:section details -->
## Zakres i rozwiązanie

- **`fixos quick` is slow.** Cache sizes are measured on a busy disk. Since
  2.2.53 the native batch is bounded by `2 × cache_timeout`; caches that
  miss it show their last complete size and the output says "częściowy
  pomiar". Check `fixos quick --json` → `safe_reclaim.measurement_complete`.
- **Docker shows "rozmiar nieznany".** `docker system df` sizes every volume
  and can take minutes. The list then shows a fast inventory (images,
  containers, volumes, unused volumes, build cache). Unused volumes may hold
  data: inspect `docker volume ls -f dangling=true` and remove only chosen
  ones. One slower run: `FIXOS_DOCKER_TIMEOUT=120 fixos cleanup --list`.
- **"Zwolniono" exceeds the `df` change.** Before 2.2.53 hardlinked files
  (uv, pnpm, conda) counted as freed; now they are `shared_hardlink_gb`.
  Other writers on the disk can still hide the gain.
- **LLM `ollama` ignores `OLLAMA_HOST`.** Fixed by ticket-074: the default
  address for the LLM and model cleanup comes from `OLLAMA_HOST`.
  `OLLAMA_BASE_URL` is a separate, LLM-only override (e.g. a proxy); unset it
  to use `OLLAMA_HOST`.
- **`goal -a`: `setup.py:version: selector version was not found`.** goal
  2.2.0 treats the computed-version `setup.py` as a source (semcod/goal#188);
  bump `VERSION` and `pyproject.toml` in a ticket until it is installed.

<!-- docs:section validation -->
## Weryfikacja

Each entry was reproduced on the same host; fixes are covered by tests in
tickets 070, 073 and 074 and by the full suite.

<!-- docs:section risks -->
## Ryzyka i następny krok

wellmanifest/reuse REUSE-006B looks only for `docs/TROUBLESHOOTING.md` or
`errors/*.md`, while wellmanifest/docs requires this location; the reuse
check needs to accept profile documents.
