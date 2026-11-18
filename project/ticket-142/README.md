# Ticket 142: Mesh host diagnostics across local interfaces and LAN/SSH peers

- **ID**: ticket-142
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — the user asked to add
  mesh network diagnostics in `fixos` so tests against a target host address run
  from every device/node in the network (2026-11-18).

## Goal and scope

Single-host checks (such as `fixos printers` running only on the primary wired
interface) report a network printer or host as healthy even when smartphones on
Wi-Fi or other PCs on another subnet/VLAN cannot reach or discover it — e.g.
because the target host has a missing default gateway (`0.0.0.0`), multicast
mDNS (`224.0.0.251:5353`) is dropped while unicast `:5353` works, or a subset
of LAN/SSH mesh nodes cannot reach the target's ports.

Scope:
1. Add built-in `mesh` diagnostic plugin (`fixos/plugins/builtin/mesh.py`) and
   register it in `PluginRegistry`:
   - Enumerates local non-container IPv4 interfaces and binds source addresses
     per interface to test TCP ports, DNS/mDNS name resolution, unicast mDNS vs
     multicast mDNS (`224.0.0.251:5353`), and optional read-only SNMPv1 MIB-II
     routing (`Default Gateway = 0.0.0.0`) on the target host.
   - Discovers peer devices on the network (ARP/neighbor table, mDNS
     `_workstation._tcp` / `_ssh._tcp`, `tailscale status --json`, concrete
     `~/.ssh/config` aliases, plus explicit `--node` entries) and executes
     bounded non-interactive SSH probes (`BatchMode=yes`) from reachable peer
     hosts against the target host, recording passive LAN/subnet status when
     SSH is unavailable.
2. Add `fixos mesh [TARGETS...]` CLI command (`fixos/cli/mesh_cmd.py`) and wire
   `--mesh` / `--node` into `fixos printers` (`fixos/cli/printers_cmd.py`).
3. Add unit tests (`tests/unit/test_mesh_plugin.py`) covering multi-interface
   source probes, remote SSH BatchMode probes, passive peer fallback, SNMP
   missing default gateway (`0.0.0.0`), multicast vs unicast mDNS drops, and
   CLI rendering/JSON output.

## Acceptance criteria

- [x] AC-01: Unit tests cover local multi-interface probes, remote SSH vantage
      probes, passive peer fallback, SNMP missing gateway (`0.0.0.0`), multicast
      vs unicast mDNS drop detection, `fixos mesh`, and `fixos printers --mesh`.
- [x] AC-02: Live `fixos mesh 192.168.188.158` and `fixos printers --mesh`
      execute across local interfaces and LAN peers and detect cross-subnet,
      gateway, and multicast mDNS anomalies on the live LAN printer.
- [ ] AC-03: Governance check, Ruff, and Wellman standards check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
