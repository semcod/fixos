# Ticket 073: docker fast inventory when docker system df times out

- **ID**: ticket-073
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

On 2026-10-13 `/var/lib/docker` held 343 GB (volumes 217 GB, overlay2 115 GB),
but `fixos cleanup` showed only "Docker - 0 MB": `docker system df` did not
answer within 120 s even at load 6.7, because it sizes all 475 volumes.
`docker image/ps/volume ls` and `docker builder du` answered in 0.1–0.3 s and
revealed 397 unused volumes, 31 dangling images and 4.3 GB build cache.

The timed-out Docker entry now carries `fast_inventory` (counts plus build
cache size, 10 s per command) and the list shows it, with "rozmiar nieznany"
instead of "0 MB". Unused volumes are data: counted only, never cleaned here.

Root cause found while verifying: `scan_service` dropped every entry below the
size threshold, so the unknown-size Docker entry (0 MB) never reached the list
at all; entries with `size_unknown` are now kept.

Live check (same host): `fixos cleanup -s docker --list` in 9.7 s shows
118 images (31 dangling), 118 containers (16 stopped), 475 volumes
(397 unused) and 4.30 GB build cache.

SESSION_EXECUTION_AUTHORIZATION: user requested improving fixos ("usprawnij fixos").

## Acceptance criteria

- [x] AC-01: tests cover inventory parsing, missing Docker, the timed-out entry and the list output.
- [x] AC-02: related cleanup suites and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
