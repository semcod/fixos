# Ticket 140: Printer digital twin: Ubuntu and Fedora guests against an emulated laser printer

- **ID**: ticket-140
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-17
- **Depends on**: ticket-139 (merged in #182)
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — the user asked to test
  the printer diagnostics on a digital twin with Ubuntu, Fedora and Windows and
  a laser printer emulator, then to continue and merge (2026-11-17).

## Goal and scope

Reproducible end-to-end evidence for `fixos printers` on real operating
systems: libvirt guests (Ubuntu 24.04, Fedora 43) on the default network and a
Brother-like laser printer emulator (IPP Everywhere via `ippeveprinter`, LPD
and raw 9100 sinks) in its own network namespace whose `BRN<mac>` name does
not resolve, reproducing the field failure of ticket-139. Windows is out of
scope here: the host had ~20 GB free and no Windows image.

## Acceptance criteria

- [x] AC-01: `twin.sh test` passes all nine scenarios on Ubuntu and Fedora and
      the emulator stores the test page from every guest.
- [ ] AC-02: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Evidence (2026-11-17, host 16 CPU / KVM)

| Guest | CUPS | Scenarios | Emulator received test page |
|-------|------|-----------|-----------------------------|
| Ubuntu 24.04.5 LTS | 2.4.7 | 19/19 checks pass | yes (IPP, PDF) |
| Fedora 43 Cloud | 2.4.x | 19/19 checks pass | yes (IPP, PDF) |

Harness defects found and fixed during the run: nested quotes in the JSON
helper; `ipptool -d which-jobs` does not override the bundled test file and
`ippeveprinter` purges completed jobs, so delivery is verified by CUPS
`job-state=completed` plus the emulator spool delta; Ubuntu CUPS keeps
`processing-to-stop-point` on completed jobs, so the alert is not a signal.
