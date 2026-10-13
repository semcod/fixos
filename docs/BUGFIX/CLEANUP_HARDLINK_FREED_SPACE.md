---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "cleanup-hardlink-freed-space",
  "kind": "bugfix",
  "version": 1,
  "title": "fixos cleanup reports only space really returned to the filesystem",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-10-13",
  "source_revision": "975468a43e78886f0c3540d527651d3de5987d0b",
  "priority": "P1",
  "evidence": ["https://github.com/semcod/fixos/pull/98"]
}
---

# fixos cleanup reports only space really returned to the filesystem

<!-- docs:section summary -->
## Cel i rezultat

On 2026-10-13 `fixos cleanup -s npm,uv,pnpm,conda,pip,go,cargo --yes`
reported 5.62 GB freed while `df` showed about 4.2 GB. After the fix
`space_freed_gb` counts only blocks that left the filesystem; bytes still
linked from elsewhere are reported as `shared_hardlink_gb`.

<!-- docs:section details -->
## Zakres i rozwiązanie

uv, pnpm and conda hardlink cache files into environments. Deleting the
cache link frees nothing while the environment link survives, but
`ServiceCleaner.cleanup_service` used the directory-size drop.
`ServiceCleaner._shared_hardlink_bytes` sums allocated bytes of regular files
whose inode has more links than are seen inside the planned paths. It is
measured before and after the cleanup command and subtracted from the
size delta. Docker keeps its daemon-based measurement.

<!-- docs:section validation -->
## Weryfikacja

`TestHardlinkAwareFreedSpace` in `tests/unit/test_service_cleanup.py` builds
real hardlinks on `tmp_path`; it fails on `fcef9db` and passes with the fix.
110 cleanup tests and `./project/governance-check.sh` pass (ticket-069).

<!-- docs:section risks -->
## Ryzyka i następny krok

The extra walk costs one `lstat` per file in the cleaned cache. Rollback:
revert ticket-069. Dry-run estimates still show the directory size as an
upper bound; making them hardlink-aware is a possible follow-up.
