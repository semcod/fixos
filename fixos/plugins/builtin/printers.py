"""Printer diagnostic plugin — CUPS (Linux/macOS) and the Windows spooler.

Diagnoses the failure modes that silently stop network printing:

* a queue whose device URI points at a host name that no longer resolves
  (typical for Brother ``BRN…``/``BRW…``, HP ``NPI…`` and similar NetBIOS
  names on networks without WINS or mDNS);
* an unreachable printer port;
* disabled or rejecting queues and jobs stuck in the queue;
* a generic or wrong driver for a printer that supports driverless IPP
  (IPP Everywhere / AirPrint);
* a stopped print service (``cups`` / ``Spooler``).

When the printer is unreachable by name it is located again by the MAC
address embedded in its host name (ARP table, optionally after a bounded
TCP sweep of the local /24), and a repair command that points the queue at
the printer's IP address is proposed.
"""

from __future__ import annotations

import ipaddress
import json
import platform
import re
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlsplit

from fixos.platform_utils import run_command
from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Finding, Severity

Runner = Callable[..., tuple[bool, str, str, int]]

DEFAULT_PORTS = {
    "ipp": 631,
    "ipps": 631,
    "http": 631,
    "https": 443,
    "lpd": 515,
    "socket": 9100,
}
PROBE_PORTS = (631, 9100, 515)
DRIVERLESS_FORMATS = ("image/pwg-raster", "image/urf", "application/pdf")
STUCK_JOB_SECONDS = 300
_HEX = re.compile(r"[0-9a-f]+")


@dataclass
class PrinterQueue:
    """Printer queue as seen by the local print system."""

    name: str
    uri: str
    model: str = ""
    enabled: bool = True
    accepting: bool = True
    pending_jobs: list[str] = field(default_factory=list)

    @property
    def scheme(self) -> str:
        return urlsplit(self.uri).scheme.lower() if "://" in self.uri else ""

    @property
    def host(self) -> str | None:
        """Network host of the queue, or ``None`` for local/dnssd/raw ports."""
        if "://" not in self.uri:
            # Windows TCP/IP port: the port name or host address is the host.
            return self.uri or None
        if self.scheme in {"usb", "dnssd", "file", "hp", "parallel", "serial"}:
            return None
        return urlsplit(self.uri).hostname

    @property
    def port(self) -> int:
        try:
            explicit = urlsplit(self.uri).port if "://" in self.uri else None
        except ValueError:
            explicit = None
        return explicit or DEFAULT_PORTS.get(self.scheme, 9100)


def mac_hint_from_hostname(host: str) -> str | None:
    """Return the MAC (or its lowercase hex suffix) embedded in a printer name.

    ``BRN3C2AF4E8C6F8`` -> ``3c2af4e8c6f8``; ``NPI8A1B2C`` -> ``8a1b2c``.
    """
    label = host.split(".", 1)[0].lower()
    for prefix in ("brn", "brw", "npi", "epson", "hp", "kmb", "xrx"):
        if label.startswith(prefix):
            tail = label[len(prefix) :].replace("-", "").replace("_", "")
            if _HEX.fullmatch(tail) and len(tail) in (6, 12):
                return tail
    match = re.search(r"([0-9a-f]{12})$", label.replace("-", ""))
    return match.group(1) if match else None


def _normalize_mac(mac: str) -> str:
    return re.sub(r"[^0-9a-f]", "", mac.lower())


def parse_neighbors(text: str) -> dict[str, str]:
    """Parse ``ip neigh``, ``arp -an`` or Windows ``arp -a`` into {mac: ip}."""
    table: dict[str, str] = {}
    ip_re = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
    mac_re = re.compile(r"\b([0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5})\b")
    for line in text.splitlines():
        ip_match, mac_match = ip_re.search(line), mac_re.search(line)
        if not ip_match or not mac_match or "FAILED" in line:
            continue
        mac = "".join(part.zfill(2) for part in re.split("[:-]", mac_match.group(1)))
        table[mac.lower()] = ip_match.group(1)
    return table


def find_ip_by_mac(hint: str, neighbors: dict[str, str]) -> str | None:
    hint = _normalize_mac(hint)
    for mac, ip in neighbors.items():
        if mac == hint or (len(hint) == 6 and mac.endswith(hint)):
            return ip
    return None


def parse_lpstat_v(text: str) -> dict[str, str]:
    """Parse ``lpstat -v`` (English and localized ``device for X: uri``)."""
    queues: dict[str, str] = {}
    for line in text.splitlines():
        match = re.search(r"(\S+):\s+(\S+:/\S*)\s*$", line)
        if match:
            queues[match.group(1)] = match.group(2)
    return queues


def parse_lpstat_p(text: str) -> dict[str, bool]:
    """Return {queue: enabled} from ``lpstat -p``."""
    states: dict[str, bool] = {}
    for line in text.splitlines():
        match = re.match(r"^printer\s+(\S+)\s+(.*)$", line)
        if match:
            states[match.group(1)] = "disabled" not in match.group(2)
    return states


def parse_lpstat_a(text: str) -> dict[str, bool]:
    states: dict[str, bool] = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            states[parts[0]] = not parts[1].startswith("not accepting")
    return states


def parse_ipp_attributes(text: str) -> dict[str, str]:
    """Parse ``ipptool -tv … get-printer-attributes.test`` output."""
    attrs: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([a-z0-9-]+) \([^)]*\) = (.*)$", line)
        if match:
            attrs[match.group(1)] = match.group(2).strip()
    return attrs


def driverless_capable(attrs: dict[str, str]) -> bool:
    formats = attrs.get("document-format-supported", "")
    return any(fmt in formats for fmt in DRIVERLESS_FORMATS)


def generic_driver(model: str) -> bool:
    lowered = model.lower()
    return any(word in lowered for word in ("generic", "foomatic", "raw queue"))


def active_fault_reasons(raw: str) -> list[str]:
    """Return non-benign IPP ``printer-state-reasons`` tokens in order."""
    faults: list[str] = []
    for part in raw.split(","):
        reason = part.strip()
        if not reason or reason == "none" or reason.endswith("-report"):
            continue
        if reason not in faults:
            faults.append(reason)
    return faults


class Plugin(DiagnosticPlugin):
    name = "printers"
    description = "Diagnostyka drukarek (CUPS/Windows spooler, sieć, sterownik)"
    platforms: ClassVar[list[str]] = ["linux", "macos", "windows"]

    def __init__(
        self,
        runner: Runner | None = None,
        resolver: Callable[[str], str | None] | None = None,
        port_open: Callable[[str, int], bool] | None = None,
        system: str | None = None,
        sweep: bool = False,
    ) -> None:
        self._run = runner or run_command
        self._resolve = resolver or _resolve
        self._port_open = port_open or _port_open
        self._system = (system or platform.system()).lower()
        self._sweep = sweep

    # ------------------------------------------------------------------ API
    def diagnose(self) -> DiagnosticResult:
        started = time.monotonic()
        findings: list[Finding] = []
        raw: dict = {"system": self._system, "queues": []}
        if self._system == "windows":
            queues = self._windows_queues(findings)
        else:
            queues = self._cups_queues(findings)

        if not queues and not findings:
            findings.append(
                Finding(
                    title="Brak skonfigurowanych drukarek",
                    severity=Severity.INFO,
                    description="System nie ma żadnej kolejki wydruku.",
                    suggestion="Dodaj drukarkę; dla drukarek sieciowych użyj "
                    "IPP Everywhere (ipp://<adres>/ipp/print).",
                )
            )
        neighbors: dict[str, str] | None = None
        for queue in queues:
            entry = {"name": queue.name, "uri": queue.uri, "model": queue.model}
            raw["queues"].append(entry)
            findings.extend(self._queue_state_findings(queue))
            host = queue.host
            if not host:
                continue
            address = self._resolve(host)
            entry["address"] = address
            if address is None:
                if neighbors is None:
                    neighbors = self._neighbors()
                findings.append(self._unresolved_finding(queue, host, neighbors, entry))
                continue
            if not self._port_open(address, queue.port):
                findings.append(
                    Finding(
                        title=f"{queue.name}: drukarka nie odpowiada",
                        severity=Severity.CRITICAL,
                        description=f"{host} ({address}) nie przyjmuje połączeń "
                        f"na porcie {queue.port}.",
                        suggestion="Sprawdź zasilanie i kabel/Wi-Fi drukarki oraz "
                        "czy nie zmieniła adresu IP (rezerwacja DHCP).",
                        data={"queue": queue.name, "address": address},
                    )
                )
                continue
            findings.extend(self._driver_findings(queue, address, entry))

        return DiagnosticResult(
            plugin_name=self.name,
            status=_worst(findings),
            findings=findings,
            raw_data=raw,
            duration_ms=(time.monotonic() - started) * 1000,
        )

    def test_print(self, queue: str, wait_seconds: int = 60) -> tuple[bool, str]:
        """Send a one-page text test job and wait for it to leave the queue."""
        text = f"fixos printer test {time.strftime('%Y-%m-%d %H:%M:%S')}"
        if self._system == "windows":
            ok, out, err, _ = self._run(
                _ps(f"'{text}' | Out-Printer -Name '{_ps_quote(queue)}'"), timeout=60
            )
            return ok, out or err
        ok, out, err, _ = self._run(
            f"printf '%s\\n' {_sh_quote(text)} | lp -d {_sh_quote(queue)}", timeout=30
        )
        if not ok:
            return False, err or out
        job = out.split()[3] if out.startswith("request id is") else ""
        deadline = time.monotonic() + wait_seconds
        while job and time.monotonic() < deadline:
            _, pending, _, _ = self._run(
                f"lpstat -W not-completed -o {_sh_quote(queue)}", timeout=10
            )
            if job not in pending:
                _, done, _, _ = self._run(
                    f"lpstat -l -W completed -o {_sh_quote(queue)}", timeout=10
                )
                block = done.split(job, 1)[-1][:300]
                if "aborted" in block or "canceled" in block:
                    return False, f"{job}: zadanie przerwane"
                return True, f"{job}: zakończone"
            time.sleep(2)
        return False, f"{job or out}: nadal w kolejce po {wait_seconds}s"

    # ----------------------------------------------------------------- CUPS
    def _cups_queues(self, findings: list[Finding]) -> list[PrinterQueue]:
        if self._system == "linux":
            _, state, _, _ = self._run("systemctl is-active cups", timeout=5)
            if state.strip() in {"inactive", "failed"}:
                findings.append(
                    Finding(
                        title="Usługa CUPS nie działa",
                        severity=Severity.CRITICAL,
                        description="Serwer wydruku CUPS jest zatrzymany.",
                        command="sudo systemctl enable --now cups",
                        data={"repair": {"op": "enable_cups", "system": self._system}},
                    )
                )
                return []
        ok, out, err, _ = self._run("LC_ALL=C lpstat -v", timeout=10)
        if not ok and "No destinations" not in (out + err):
            if "not found" in err or "command not found" in err:
                findings.append(
                    Finding(
                        title="Brak klienta CUPS",
                        severity=Severity.WARNING,
                        description="Polecenie lpstat nie jest dostępne.",
                        suggestion="Zainstaluj pakiet cups / cups-client.",
                    )
                )
            return []
        uris = parse_lpstat_v(out)
        _, p_out, _, _ = self._run("LC_ALL=C lpstat -p", timeout=10)
        _, a_out, _, _ = self._run("LC_ALL=C lpstat -a", timeout=10)
        enabled, accepting = parse_lpstat_p(p_out), parse_lpstat_a(a_out)
        queues = []
        for name, uri in uris.items():
            _, opts, _, _ = self._run(f"lpoptions -p {_sh_quote(name)}", timeout=10)
            model = re.search(r"printer-make-and-model='([^']*)'", opts)
            _, jobs, _, _ = self._run(
                f"LC_ALL=C lpstat -W not-completed -o {_sh_quote(name)}", timeout=10
            )
            queues.append(
                PrinterQueue(
                    name=name,
                    uri=uri,
                    model=model.group(1) if model else "",
                    enabled=enabled.get(name, True),
                    accepting=accepting.get(name, True),
                    pending_jobs=_stuck_jobs(jobs),
                )
            )
        return queues

    def _queue_state_findings(self, queue: PrinterQueue) -> list[Finding]:
        found = []
        windows = self._system == "windows"
        if not queue.enabled or not queue.accepting:
            cmd = (
                _ps(f"Resume-Printer -Name '{_ps_quote(queue.name)}'")
                if windows
                else f"sudo cupsenable {_sh_quote(queue.name)} && "
                f"sudo cupsaccept {_sh_quote(queue.name)}"
            )
            found.append(
                Finding(
                    title=f"{queue.name}: kolejka wstrzymana",
                    severity=Severity.WARNING,
                    description="Kolejka jest wyłączona lub odrzuca zadania "
                    "(zwykle po wcześniejszym błędzie połączenia).",
                    command=cmd,
                    data={
                        "queue": queue.name,
                        "repair": {
                            "op": "resume_queue",
                            "system": self._system,
                            "queue": queue.name,
                        },
                    },
                )
            )
        if queue.pending_jobs:
            found.append(
                Finding(
                    title=f"{queue.name}: zablokowane zadania "
                    f"({len(queue.pending_jobs)})",
                    severity=Severity.WARNING,
                    description="Zadania czekają w kolejce dłużej niż "
                    f"{STUCK_JOB_SECONDS // 60} min: "
                    + ", ".join(queue.pending_jobs[:5]),
                    suggestion="Napraw połączenie z drukarką, potem wyczyść "
                    "kolejkę i wydrukuj ponownie.",
                    command=(
                        _ps(
                            f"Get-PrintJob -PrinterName '{_ps_quote(queue.name)}' "
                            "| Remove-PrintJob"
                        )
                        if windows
                        else f"cancel -a {_sh_quote(queue.name)}"
                    ),
                    data={
                        "queue": queue.name,
                        "jobs": queue.pending_jobs,
                        "repair": {
                            "op": "clear_jobs",
                            "system": self._system,
                            "queue": queue.name,
                        },
                    },
                )
            )
        return found

    def _unresolved_finding(
        self,
        queue: PrinterQueue,
        host: str,
        neighbors: dict[str, str],
        entry: dict,
    ) -> Finding:
        hint = mac_hint_from_hostname(host)
        address = find_ip_by_mac(hint, neighbors) if hint else None
        if hint and address is None and self._sweep:
            self._tcp_sweep()
            address = find_ip_by_mac(hint, self._neighbors())
        entry["located_address"] = address
        description = (
            f"Kolejka używa adresu '{queue.uri}', ale nazwy '{host}' nie da się "
            "rozwiązać (brak wpisu w DNS, mDNS i /etc/hosts). Zadania nie "
            "docierają do drukarki i wiszą w kolejce."
        )
        if address is None:
            return Finding(
                title=f"{queue.name}: nie można rozwiązać nazwy drukarki",
                severity=Severity.CRITICAL,
                description=description,
                suggestion=(
                    "Nie znaleziono drukarki w tablicy ARP"
                    + (f" (MAC …{hint})" if hint else "")
                    + ". Uruchom `fixos printers --scan` albo odczytaj IP z "
                    "panelu drukarki i ustaw je w kolejce."
                ),
                data={"queue": queue.name, "host": host, "mac_hint": hint},
            )
        description += f" Drukarka znaleziona po MAC pod adresem {address}."
        return Finding(
            title=f"{queue.name}: nie można rozwiązać nazwy drukarki",
            severity=Severity.CRITICAL,
            description=description,
            suggestion="Przepnij kolejkę na adres IP i ustaw rezerwację DHCP "
            "dla tej drukarki na routerze.",
            command=self._repoint_command(queue, address),
            data={
                "queue": queue.name,
                "host": host,
                "address": address,
                "repair": {
                    "op": "repoint_queue",
                    "system": self._system,
                    "queue": queue.name,
                    "address": address,
                },
            },
        )

    def _driver_findings(
        self, queue: PrinterQueue, address: str, entry: dict
    ) -> list[Finding]:
        if self._system == "windows" or queue.scheme not in {
            "ipp",
            "ipps",
            "lpd",
            "socket",
            "http",
        }:
            return []
        if not self._port_open(address, 631):
            return []
        ok, out, _, _ = self._run(
            f"ipptool -tv ipp://{address}/ipp/print get-printer-attributes.test",
            timeout=15,
        )
        if not ok:
            return []
        attrs = parse_ipp_attributes(out)
        entry["ipp"] = {
            k: attrs.get(k)
            for k in (
                "printer-make-and-model",
                "printer-state",
                "printer-state-reasons",
            )
        }
        found = []
        faults = active_fault_reasons(attrs.get("printer-state-reasons", "none"))
        if faults:
            found.append(
                Finding(
                    title=f"{queue.name}: drukarka zgłasza problem",
                    severity=Severity.WARNING,
                    description=f"printer-state-reasons = {', '.join(faults)}",
                    suggestion="Sprawdź panel drukarki (papier, toner, pokrywa).",
                    data={"queue": queue.name, "reasons": faults},
                )
            )
        if driverless_capable(attrs) and (
            generic_driver(queue.model) or queue.scheme in {"lpd", "socket"}
        ):
            found.append(
                Finding(
                    title=f"{queue.name}: przestarzały sterownik/protokół",
                    severity=Severity.WARNING,
                    description=f"Kolejka używa '{queue.model or queue.scheme}', a "
                    "drukarka obsługuje druk bez sterownika (IPP Everywhere).",
                    command=self._repoint_command(queue, address),
                    data={
                        "queue": queue.name,
                        "address": address,
                        "repair": {
                            "op": "repoint_queue",
                            "system": self._system,
                            "queue": queue.name,
                            "address": address,
                        },
                    },
                )
            )
        return found

    def _repoint_command(self, queue: PrinterQueue, address: str) -> str:
        if self._system == "windows":
            port = f"IP_{address}"
            return _ps(
                f"if (-not (Get-PrinterPort -Name '{port}' -ErrorAction "
                f"SilentlyContinue)) {{ Add-PrinterPort -Name '{port}' "
                f"-PrinterHostAddress '{address}' }}; Set-Printer -Name "
                f"'{_ps_quote(queue.name)}' -PortName '{port}'"
            )
        name = _sh_quote(queue.name)
        backup = (
            "sudo cp /etc/cups/printers.conf "
            "/etc/cups/printers.conf.bak-$(date +%Y%m%d%H%M%S) && "
            if self._system == "linux"
            else ""
        )
        return (
            f"{backup}sudo lpadmin -p {name} -E -v ipp://{address}/ipp/print "
            f"-m everywhere && sudo cupsenable {name} && sudo cupsaccept {name}"
        )

    # -------------------------------------------------------------- Windows
    def _windows_queues(self, findings: list[Finding]) -> list[PrinterQueue]:
        _, status, _, _ = self._run(_ps("(Get-Service Spooler).Status"), timeout=15)
        if status.strip() and status.strip() != "Running":
            findings.append(
                Finding(
                    title="Bufor wydruku (Spooler) nie działa",
                    severity=Severity.CRITICAL,
                    description=f"Usługa Spooler ma stan {status.strip()}.",
                    command=_ps("Restart-Service Spooler -Force"),
                    data={"repair": {"op": "restart_spooler", "system": "windows"}},
                )
            )
            return []
        ok, out, _, _ = self._run(
            _ps(
                "Get-Printer | ForEach-Object { $p = Get-PrinterPort -Name "
                "$_.PortName -ErrorAction SilentlyContinue; $j = @(Get-PrintJob "
                "-PrinterName $_.Name -ErrorAction SilentlyContinue | Where-Object "
                "{ $_.SubmittedTime -lt (Get-Date).AddMinutes(-5) }); "
                "[pscustomobject]@{Name=$_.Name; Port=$_.PortName; "
                "Host=$p.PrinterHostAddress; Driver=$_.DriverName; "
                "Status=[string]$_.PrinterStatus; Jobs=@($j | ForEach-Object "
                "{ [string]$_.Id })} } | ConvertTo-Json -Depth 3"
            ),
            timeout=30,
        )
        if not ok or not out.strip():
            return []
        data = json.loads(out)
        queues = []
        for item in data if isinstance(data, list) else [data]:
            queues.append(
                PrinterQueue(
                    name=item.get("Name", ""),
                    uri=item.get("Host") or "",
                    model=item.get("Driver") or "",
                    enabled=item.get("Status") not in ("Paused", "1"),
                    pending_jobs=[str(j) for j in item.get("Jobs") or []],
                )
            )
        return queues

    # -------------------------------------------------------------- network
    def _neighbors(self) -> dict[str, str]:
        if self._system == "linux":
            ok, out, _, _ = self._run("ip neigh", timeout=5)
            if ok:
                return parse_neighbors(out)
        _, out, _, _ = self._run(
            "arp -an" if self._system != "windows" else "arp -a", timeout=10
        )
        return parse_neighbors(out)

    def _tcp_sweep(self) -> None:
        """Touch every host of the local /24 networks to populate ARP."""
        hosts: list[str] = []
        for net in _local_networks():
            hosts.extend(str(h) for h in net.hosts())
        with ThreadPoolExecutor(max_workers=64) as pool:
            list(pool.map(lambda h: self._port_open(h, 631, 0.3), hosts[:1024]))


def _stuck_jobs(text: str, now: float | None = None) -> list[str]:
    """Return ids of jobs listed by ``lpstat -o`` older than the threshold."""
    jobs = []
    now = now or time.time()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        stamp = " ".join(parts[3:])
        if re.search(r" [A-Z]{2,5}$", stamp):
            stamp = stamp.rsplit(" ", 1)[0]  # strip zone name, e.g. CET
        age = None
        for fmt in (
            "%a %d %b %Y %I:%M:%S %p",
            "%a %d %b %Y %H:%M:%S",
            "%a %b %d %H:%M:%S %Y",
        ):
            try:
                age = now - time.mktime(time.strptime(stamp, fmt))
                break
            except ValueError:
                continue
        if age is None or age > STUCK_JOB_SECONDS:
            jobs.append(parts[0])
    return jobs


def _local_networks() -> list[ipaddress.IPv4Network]:
    nets = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 9))
        local = probe.getsockname()[0]
        probe.close()
        nets.append(ipaddress.ip_network(f"{local}/24", strict=False))
    except OSError:
        pass
    return nets


def _resolve(host: str) -> str | None:
    try:
        return socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except (socket.gaierror, UnicodeError, IndexError):
        return None


def _port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _worst(findings: list[Finding]) -> Severity:
    order = [Severity.OK, Severity.INFO, Severity.WARNING, Severity.CRITICAL]
    return max((f.severity for f in findings), key=order.index, default=Severity.OK)


def _sh_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def _ps_quote(value: str) -> str:
    return value.replace("'", "''")


def _ps(script: str) -> str:
    return 'powershell -NoProfile -Command "' + script.replace('"', '\\"') + '"'
