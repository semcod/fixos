# Printer digital twin

End-to-end check of `fixos printers` on real operating systems against an
emulated network laser printer. It reproduces the field failure from
ticket-139: a CUPS queue pointing at a Brother NetBIOS name (`BRN<mac>`) that
no resolver on the LAN knows.

```
            libvirt "default" network 192.168.122.0/24 (virbr0)
   ┌───────────────────┬────────────────────┬──────────────────────────┐
   │ fixos-twin-ubuntu │ fixos-twin-fedora  │ netns fixos-printer      │
   │ Ubuntu 24.04 VM   │ Fedora 43 VM       │ 192.168.122.50           │
   │ CUPS + fixos      │ CUPS + fixos       │ MAC 3c:2a:f4:00:00:01    │
   └───────────────────┴────────────────────┤ "BRN3C2AF4000001"        │
                                            │ 631 IPP Everywhere       │
                                            │ 515 LPD, 9100 raw sinks  │
                                            └──────────────────────────┘
```

* `printer-emulator.sh` – network namespace with a Brother OUI MAC running
  `ippeveprinter` (DNS-SD off, so the name never resolves for guests) and
  `job_sink.py` (LPD and raw 9100). Received jobs are kept in
  `$TWIN_DIR/spool`.
* `twin.sh` – creates thin-overlay guests from cloud images, installs CUPS
  and the current checkout of fixos, runs the scenarios.
* `scenarios.sh` – runs in each guest as root: breaks the print system,
  checks the diagnosis of `fixos printers`, applies `--fix -y`, verifies.

| # | Scenario | Expected |
|---|----------|----------|
| S1 | queue `lpd://BRN…/BINARY_P1`, printer not in ARP | CRITICAL unresolvable, no blind repair |
| S2 | same, `--scan` | printer located by MAC, repair proposed |
| S3 | `--fix -y --scan` | queue becomes `ipp://<ip>/ipp/print` (IPP Everywhere), healthy |
| S4 | `--test-print` | job completes and the emulator records it |
| S5 | raw `lpd://<ip>` and `socket://<ip>:9100` queues | outdated driver/protocol, fixed to IPP Everywhere |
| S6 | `cupsdisable` | paused queue, re-enabled |
| S7 | queue to a dead address | printer not responding |
| S8 | `cups` stopped | service stopped, started again |
| S9 | job older than 5 min on the dead queue | stuck jobs, queue cleared |

## Run

Requires KVM/libvirt, `cloud-localds`, `ippeveprinter` (CUPS 2.4) and about
1.2 GB for the base images plus ~4 GB for overlays.

```bash
D=/var/lib/libvirt/images/fixos-twin
sudo mkdir -p $D
sudo curl -sSLo $D/ubuntu-24.04.img \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
sudo curl -sSLo $D/fedora-43.qcow2 \
  https://download.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2
sudo tests/twin/printers/twin.sh up
sudo tests/twin/printers/twin.sh test     # ~7 min, S9 waits for job aging
sudo tests/twin/printers/twin.sh destroy
```

Windows is not part of this twin yet: it needs a Windows evaluation image and
~20 GB of disk. The Windows backend is covered by unit tests with recorded
PowerShell output.
