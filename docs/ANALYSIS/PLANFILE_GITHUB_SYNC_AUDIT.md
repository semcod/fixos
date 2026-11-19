---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "planfile-github-sync-audit",
  "kind": "analysis",
  "version": 2,
  "title": "Planfile-GitHub synchronization, backlog reconciliation, and Heyasa queue audit",
  "status": "implemented",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-11-19",
  "source_revision": "dbe080ac4d15980f160d501365c882fc17e4662d",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/fixos/issues/170",
    "https://github.com/semcod/fixos/issues/171",
    "https://github.com/semcod/fixos/issues/174",
    "https://github.com/semcod/fixos/issues/202",
    "https://github.com/semcod/fixos/issues/206",
    "https://github.com/semcod/fixos/issues/209",
    "https://github.com/semcod/fixos/pull/208",
    "https://github.com/semcod/fixos/pull/214",
    "https://github.com/semcod/fixos/pull/215",
    "https://github.com/semcod/planfile/issues/400",
    "https://github.com/semcod/planfile/issues/403",
    "https://github.com/subactor/coding-agent/issues/320",
    "https://github.com/subactor/coding-agent/issues/322",
    "https://github.com/subactor/coding-agent/issues/323",
    "https://github.com/heyasa/heyasa/issues/891"
  ]
}
---

# Planfile-GitHub synchronization, backlog reconciliation, and Heyasa queue audit

<!-- docs:section summary -->
## Cel i rezultat

Completes Planfile-GitHub bidirectional reconciliation (`#170` / `PLF-21821`), legacy workspace disposition (`#174` / `PLF-21812`), and end-to-end Heyasa → Willman → Central Planfile (`127.0.0.1:18769`) → Coding Agent → OneDev → Independent Validator (`ifuri-validator-agent`) loop verification (`#171` / `PLF-21822`) on `semcod/fixos`, with upstream defects isolated to their owning repositories (`semcod/planfile#403`, `subactor/coding-agent#320`, `subactor/coding-agent#322`).

<!-- docs:section details -->
## Zakres i rozwiązanie

- **Bidirectional sync & historical audit (`#170`)**: Host timer `fixos-planfile-sync.timer` runs `planfile sync retry --max-tickets 5` and `planfile sync github --direction from --timeout 180` with SQLite revision/worker fencing. Closed `#130`–`#133`, `#162`–`#169`, `#182`, `#183`, `#185` reconciled without duplicates; 23 unmapped `done` tickets classified (`16 executed`, `7 no-change`).
- **Central queue & Heyasa intake (`#171` AC 1–4, 6)**: Restarted stalled `18769` index (`probe_central_planfile_discovery` -> `HTTP 200 ready`, 28,225 tickets), keeping runtime image `819378c91382` (`0.1.126` / `123d5224`) active. Verified `heyasa.fleet_backlog.scan_repository_backlog` sees open work in both `backlog.yaml` and `current.yaml` after `move_ticket` promotion without reviving `done` history, and verified `proc://heyasa/housekeeping/autonomy-auto-qualify/v1` gates execution behind `subactor:autonomy`.
- **Upstream owner issues filed (`#171` AC 6)**: `semcod/planfile#403` (`reconcile_index` > `2.0s` triggers 200s rebuilds), `subactor/coding-agent#320` (`search/issues` `per_page=100` global truncation + static `assigned_to="bot:coding-agent"`), `subactor/coding-agent#322` (`_prior_project_attempt` skips released `project-session.json` under `0.20.162` `status-projection` on `PLF-28445` / `#206` / `ticket-161`), and `subactor/coding-agent#323` (`.subactor/cache/execution/` handling in `reconcile_merged_session`).

<!-- docs:section validation -->
## Weryfikacja

- **Sync canary (`#170` AC 3)**: `PLF-21826` (`semcod/fixos#202`) verified `OPEN` -> `CLOSED` with `planfile.sync-receipt/v1` `dc1e1c2a6246172715b204f01c8538b2a96f17117aee8f14ec0a22a7af24a1ac`.
- **End-to-end Heyasa merge canary (`#171` AC 5)**: `PLF-21832` (`semcod/fixos#209`) -> qualified `subactor:autonomy` -> ingested into `18769` as `PLF-28514` (`subactor.process-envelope.v2`) -> dispatched via `WillmanEngineAdapter` (`a2250ea9-8214-5fc7-aa07-77a9ee6282bf`, job `d76434cc-be65-40b0-a0f3-3308727182d5`) -> claimed with fencing -> native `ticket-164` worktree -> implementation & pytest PASS (`1319 passed`) -> `PR #214` (`head: 57cea56f2a52e03077579f6d71cf6ad418181811`) -> `onedev/local-verify` PASS -> `app/ifuri-validator-agent` exact-head `APPROVED` (`PRR_kwDORTIK388AAAABY7bH5A`) & `MERGED` (`db845b77d3c335f2e9cca50fc01eef4cd141cbe5`) -> `willman.project-observation/v1` (`status: "merged"`, `writer_released: true`).

<!-- docs:section risks -->
## Ryzyka i następny krok

- **`#206` (`PLF-21827` / `PLF-28445`)**: Native worktree `.worktrees/ticket-161--project-job-26a7da64` (`656f6cdb`, `lease.phase="released"`) remains fenced under `agent:coding-agent` pending `subactor/coding-agent#322` (`PLF-20363`); baseline `STD-ADOPTION-DRIFT` from `PR #207` was resolved on `main` via `PR #208` (`da0ea36a`).
- **`#174` (`PLF-21812`)**: Completed via human-authorized `archive-and-retire` disposition (`docs/analysis/legacy-workspace-reconciliation.md` v4).
