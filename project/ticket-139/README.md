# Ticket 139: Printer diagnostics and repair across Linux, macOS and Windows

- **ID**: ticket-139
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-17
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — the user asked to create
  printer diagnostics and repair in semcod/fixos and publish it with `goal -a`
  (2026-11-17).

## Goal and scope

On 2026-11-17 a Brother HL-L5200DW on the LAN did not print: the CUPS queue
used `lpd://BRN3C2AF4E8C6F8/BINARY_P1`, the NetBIOS name did not resolve (no
DNS, mDNS or WINS), jobs hung and CUPS stopped them as unresponsive; the queue
also used a generic colour PCL driver for a mono printer that supports IPP
Everywhere. The printer was found by the MAC embedded in its name in the ARP
table and the queue was repointed to `ipp://<ip>/ipp/print -m everywhere`.

Scope: turn that procedure into a `printers` diagnostic plugin and a
`fixos printers` command for CUPS (Linux, macOS) and the Windows spooler.

## Acceptance criteria

- [x] AC-01: Unit tests cover unresolvable vendor host names (relocated by MAC),
      unreachable port, paused queue, stuck jobs, generic driver on a
      driverless printer, stopped CUPS/Spooler, Windows port repointing and
      the test print.
- [x] AC-02: Live `fixos printers` reports the repaired Brother queue as healthy
      and `--test-print` completes.
- [ ] AC-03: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
