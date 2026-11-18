---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "planfile-github-sync-audit",
  "kind": "analysis",
  "version": 1,
  "title": "Planfile-GitHub synchronization, backlog reconciliation, and Heyasa queue audit",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-11-18",
  "source_revision": "f989c7103ae2d3870639d9bfb4fc18a1e4d29605",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/fixos/issues/170",
    "https://github.com/semcod/fixos/issues/202",
    "https://github.com/semcod/planfile/issues/400",
    "https://github.com/heyasa/heyasa/issues/891"
  ]
}
---

# Planfile-GitHub synchronization, backlog reconciliation, and Heyasa queue audit

<!-- docs:section summary -->
## Cel i rezultat

Reconciles `.planfile/` state for `semcod/fixos` (`#170` / `PLF-21821`), restores bidirectional GitHub sync after deduplicating nested HTML markers on closed `#74`/`#75` (upstream parser hardening tracked in `semcod/planfile#400`), deploys a persistent user-systemd retry/inbound worker, classifies all 23 unmapped historical `done` records without publishing noise, and records upstream blockers for `#171` and `#174`.

<!-- docs:section details -->
## Zakres i rozwiązanie

- **Bidirectional worker (`#170` AC 1–2)**: Unregistered `.github/workflows/planfile-github-sync.yml` (`404` on GitHub Actions API) is superseded on the host by `fixos-planfile-sync.timer` (`Persistent=true`, `OnUnitInactiveSec=10min`) invoking `planfile sync retry --max-tickets 5` (SQLite `revision` + `worker_token` fencing, `retry_pauses` cooldowns, `enqueue_on_done: true`) and `planfile sync github --direction from --timeout 180`.
- **Ticket & issue reconciliation (`#170` AC 4)**: Closed GitHub issues `#130`–`#133` imported without duplicates as `GITHUB-130`..`133` (`done`); `PLF-21813`..`21820` (`#162`–`#169`), `PLF-21823` (`PR #182` `8524601`), and `PLF-21824`..`21825` (`#183`, `#185`) reconciled to `done`; `PLF-033` delivered via `.governance/standards-lock.json`; `PLF-21812` (`#174`) retained as `blocked`.

| Unmapped `done` group (count) | Classification | Verified evidence |
|---|---|---|
| `PLF-001`, `PLF-014`, `PLF-015`, `PLF-017`..`024`, `PLF-034`, `PLF-036`, `PLF-037`, `PLF-039`, `PLF-21811` (16) | `executed` | Merged commits `fd093e0`, `43fa26b`, `266f85f`, `3ee557d`, `b0fe714`, `81b2e18`, and `safetytwin#2` (`394e86f`); `integration` cleared to `[]`. |
| `PLF-025`, `task_1790352032_1`, `PLF-027`..`030`, `PLF-035` (7) | `no-change` | Bounded Koru/Willman diagnostic observations (`exit_code: 0`); no source diff required; `integration` cleared to `[]`. |

<!-- docs:section validation -->
## Weryfikacja

- **Live canary (`#170` AC 3)**: `PLF-21826` mapped to `semcod/fixos#202` via CLI `ticket create --sync`, updated via Python SDK (`OPEN` read-back verified), transitioned to `done` (`enqueue_on_done` queued `pending` job), and closed remotely by `planfile sync retry` (`CLOSED` read-back `2026-11-18T19:56:15Z`), emitting `planfile.sync-receipt/v1` receipt `dc1e1c2a6246172715b204f01c8538b2a96f17117aee8f14ec0a22a7af24a1ac`.
- **Sprint contract**: All 14 `.planfile/sprints/*.yaml` files pass `planfile validate schema --file-type sprint` (`v1.1`); `tests/unit/test_planfile_sprint_contract.py` verifies writer-to-validator roundtrip and SHA-256 CAS backup migration (`PR #203`).

<!-- docs:section risks -->
## Ryzyka i następny krok

- **`#171` (`PLF-21822`)**: `heyasa.fleet_backlog` inspects `current.yaml` (`open: 0`) rather than `backlog.yaml`, while `127.0.0.1:18769/tickets/discovery` returns `HTTP 503 {"detail":"ticket_index_stale"}`; tracked under upstream owner `heyasa/heyasa#891`.
- **`#174` (`PLF-21812`)**: `wellmanifest/new-project#576` merged (`de22d44`), while `#575`, human `archive-and-retire` disposition, and `STARTER-029` lease remain required before modifying `.subactor/leases/` or `ticket/110`.
