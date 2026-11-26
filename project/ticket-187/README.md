# Ticket 187: Clean Flatpak browser caches (Firefox, Edge) in fixos cleanup

- **ID**: ticket-187
- **Owner**: agent:claude-code (SESSION_EXECUTION_AUTHORIZATION from user request)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-26

## Goal and scope

On Fedora with Flatpak browsers, `fixos cleanup` did not see their caches: Flatpak sets
`XDG_CACHE_HOME` to `~/.var/app/<app-id>/cache`, while `SERVICE_PATHS` and the cleanup commands only
listed `~/.cache/...`. On the reporting host this hid 825 MB of Firefox HTTP cache
(`~/.var/app/org.mozilla.firefox/cache/mozilla`). Add the Flatpak cache paths of Firefox and Edge
to both the scanner and the `rm -rf` cleanup commands.

Out of scope: `~/.var/app/*/cache/tmp` (Firefox keeps in-progress download and temp files there)
and other Flatpak apps.

## Acceptance criteria

- [x] AC-01: `ServiceDataScanner.scan_service` reports the Flatpak cache path for Firefox and Edge,
  `get_cleanup_command` removes it, risk level stays SAFE; new and existing cleanup tests pass
  together with `./project/governance-check.sh`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

<!-- ticket-radar:start -->
## Ticket Radar

Initial planned-scope estimate; advisory only, not execution or merge approval.

Assessment unavailable: runtime not installed.
<!-- ticket-radar:end -->
