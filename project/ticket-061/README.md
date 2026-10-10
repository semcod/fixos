# Ticket 061: optimize bottlenecks with rust fast scan and visual shell dashboard

- **ID**: ticket-061
- **Owner**: antigravity:fixos-061-20261010
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-10

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested performance optimization of FixOS, identifying bottlenecks and accelerating them with Rust so they are reused by the Python package (addressing long loading times in `fixos cleanup` and investigating other commands), creating a graphical shell representation (comprehensive visual scan) to clearly spot system problems, and providing automated intervention where cleanup and killing processes is verified safe.

## Acceptance criteria

- [x] AC-01: Lazy loading of CLI subcommands eliminates eager import of heavy libraries on startup, reducing `fixos` and `fixos cleanup` baseline latency.
- [x] AC-02: Rust `fixos-native` provides batch and directory measurement primitives integrated into `native_scan`, `service_scanner` and `cache_discovery` with verified fast Python fallbacks.
- [x] AC-03: `fixos cleanup` bounds Docker daemon probe timeout to prevent hanging.
- [x] AC-04: Graphical shell dashboard (`fixos shell` visual mode / dashboard) visualizes resource status, identifies bottlenecks (disk/cache/processes), and provides safe automated intervention with dry-run support.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
