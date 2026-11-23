"""DNS diagnostic and deterministic repair plugin (systemd-resolved, NetworkManager, resolv.conf)."""

from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Finding, Severity

DEFAULT_PROBE_HOSTS: tuple[str, ...] = ("api.github.com", "pypi.org")
DEFAULT_UPSTREAM_DNS: tuple[str, ...] = ("1.1.1.1", "8.8.8.8")
DEFAULT_FALLBACK_DNS: tuple[str, ...] = ("9.9.9.9", "1.0.0.1")
RESOLVED_DROPIN_PATH = Path("/etc/systemd/resolved.conf.d/99-fixos-dns.conf")
TIMEOUT_WARNING_THRESHOLD = 100
LATENCY_WARNING_MS = 1000.0

_LINK_HEADER_RE = re.compile(r"^Link\s+\d+\s+\(([^)]+)\)\s*$")
_STAT_KV_RE = re.compile(r"^\s*([A-Za-z0-9 ()_-]+?):\s+(\d+)\s*$")


def is_private_ipv4(address: str) -> bool:
    """Return True when ``address`` is a private, loopback, or link-local IPv4."""
    try:
        ip_obj = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    return ip_obj.version == 4 and (
        ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    )


def parse_resolv_conf(text: str) -> dict[str, list[str]]:
    """Parse ``/etc/resolv.conf`` into nameservers, search domains, and options."""
    nameservers: list[str] = []
    search_domains: list[str] = []
    options: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        key = parts[0].lower()
        values = parts[1:]
        if key == "nameserver" and values:
            nameservers.append(values[0])
        elif key in ("search", "domain") and values:
            search_domains.extend(values)
        elif key == "options" and values:
            options.extend(values)
    return {
        "nameservers": nameservers,
        "search_domains": search_domains,
        "options": options,
    }


def parse_resolvectl_statistics(text: str) -> dict[str, int]:
    """Extract transaction and timeout counters from ``resolvectl statistics``."""
    mapping = {
        "Total Transactions": "total_transactions",
        "Current Transactions": "current_transactions",
        "Cache Hits": "cache_hits",
        "Cache Misses": "cache_misses",
        "Total Timeouts": "total_timeouts",
        "Total Failure Responses": "failure_responses",
    }
    stats: dict[str, int] = {}
    for line in text.splitlines():
        match = _STAT_KV_RE.match(line)
        if not match:
            continue
        label, value = match.group(1).strip(), int(match.group(2))
        if label in mapping:
            stats[mapping[label]] = value
    return stats


def parse_resolvectl_status(text: str) -> dict[str, Any]:
    """Parse ``resolvectl status`` into global settings and per-link DNS state."""
    global_dns: list[str] = []
    fallback_dns: list[str] = []
    links: list[dict[str, Any]] = []
    section: str | None = None
    current_link: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped == "Global":
            section = "global"
            current_link = None
            continue
        link_match = _LINK_HEADER_RE.match(stripped)
        if link_match:
            section = "link"
            current_link = {
                "device": link_match.group(1),
                "current_dns": None,
                "dns_servers": [],
                "dns_domains": [],
                "default_route": False,
            }
            links.append(current_link)
            continue

        if ":" not in stripped:
            continue
        key, raw_val = stripped.split(":", 1)
        key = key.strip()
        val = raw_val.strip()

        if section == "global":
            if key == "DNS Servers":
                global_dns.extend(val.split())
            elif key == "Fallback DNS Servers":
                fallback_dns.extend(val.split())
        elif section == "link" and current_link is not None:
            if key == "Current DNS Server":
                current_link["current_dns"] = val
            elif key == "DNS Servers":
                current_link["dns_servers"].extend(val.split())
            elif key == "DNS Domain":
                current_link["dns_domains"].extend(val.split())
            elif key == "Default Route":
                current_link["default_route"] = val.lower() == "yes"

    return {
        "global_dns": global_dns,
        "fallback_dns": fallback_dns,
        "links": links,
    }


def _run_text_command(command: Sequence[str], timeout: int = 8) -> tuple[bool, str, str]:
    """Run a bounded read-only/repair command without invoking a shell."""
    try:
        proc = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "", str(exc)


def _active_nm_connections_by_device() -> dict[str, str]:
    """Map active NetworkManager device names to connection profile names."""
    if not shutil.which("nmcli"):
        return {}
    ok, stdout, _ = _run_text_command(
        ["nmcli", "-t", "-f", "NAME,DEVICE", "con", "show", "--active"], timeout=5
    )
    if not ok:
        return {}
    mapping: dict[str, str] = {}
    for line in stdout.splitlines():
        if ":" not in line:
            continue
        name, device = line.rsplit(":", 1)
        if name and device:
            mapping[device.strip()] = name.strip()
    return mapping


def render_resolved_dropin(
    upstream_dns: Sequence[str] = DEFAULT_UPSTREAM_DNS,
    fallback_dns: Sequence[str] = DEFAULT_FALLBACK_DNS,
) -> str:
    """Render deterministic ``systemd-resolved`` drop-in content."""
    dns_line = " ".join(upstream_dns)
    fallback_line = " ".join(fallback_dns)
    return (
        "[Resolve]\n"
        f"DNS={dns_line}\n"
        f"FallbackDNS={fallback_line}\n"
        "DNSSEC=no\n"
        "Cache=yes\n"
    )


def build_repair_plan(
    status: dict[str, Any],
    nm_connections: dict[str, str] | None = None,
    upstream_dns: Sequence[str] = DEFAULT_UPSTREAM_DNS,
    fallback_dns: Sequence[str] = DEFAULT_FALLBACK_DNS,
    dropin_path: Path = RESOLVED_DROPIN_PATH,
) -> list[dict[str, Any]]:
    """Build a deterministic, reversible DNS repair plan for Linux hosts."""
    plan: list[dict[str, Any]] = []
    dropin_content = render_resolved_dropin(upstream_dns, fallback_dns)
    plan.append(
        {
            "step": "write_resolved_dropin",
            "description": f"Zapisz drop-in systemd-resolved ({dropin_path})",
            "path": str(dropin_path),
            "content": dropin_content,
            "command": [
                "sudo",
                "install",
                "-d",
                "-m",
                "0755",
                str(dropin_path.parent),
            ],
        }
    )

    connections = nm_connections if nm_connections is not None else {}
    for link in status.get("links", []):
        if not link.get("default_route"):
            continue
        device = str(link.get("device") or "")
        servers = [str(s) for s in link.get("dns_servers", [])]
        if not servers:
            continue
        if all(is_private_ipv4(server) for server in servers) and device in connections:
            conn_name = connections[device]
            combined_dns = list(dict.fromkeys([*upstream_dns, *servers]))
            domains = [str(d) for d in link.get("dns_domains", []) if d]
            mod_cmd = [
                "sudo",
                "nmcli",
                "con",
                "mod",
                conn_name,
                "ipv4.dns",
                " ".join(combined_dns),
                "ipv4.ignore-auto-dns",
                "yes",
            ]
            if domains:
                mod_cmd.extend(["ipv4.dns-search", " ".join(domains)])
            plan.append(
                {
                    "step": f"nmcli_dns_{device}",
                    "description": (
                        f"Ustaw DNS ({', '.join(combined_dns)}) na połączeniu "
                        f"'{conn_name}' ({device})"
                    ),
                    "command": mod_cmd,
                }
            )
            plan.append(
                {
                    "step": f"nmcli_reapply_{device}",
                    "description": f"Zastosuj ustawienia DNS na interfejsie {device}",
                    "command": ["sudo", "nmcli", "device", "reapply", device],
                }
            )

    plan.append(
        {
            "step": "restart_resolved",
            "description": "Zrestartuj usługę systemd-resolved",
            "command": ["sudo", "systemctl", "restart", "systemd-resolved"],
        }
    )
    plan.append(
        {
            "step": "flush_dns_cache",
            "description": "Wyczyść pamięć podręczną DNS (resolvectl flush-caches)",
            "command": ["resolvectl", "flush-caches"],
        }
    )
    return plan


def apply_dns_repair(
    plan: Sequence[dict[str, Any]], dry_run: bool = False
) -> list[dict[str, Any]]:
    """Execute or simulate a DNS repair plan built by ``build_repair_plan``."""
    results: list[dict[str, Any]] = []
    for item in plan:
        step = str(item.get("step", "unknown"))
        cmd = [str(part) for part in item.get("command", [])]
        if dry_run:
            results.append(
                {
                    "step": step,
                    "description": item.get("description", ""),
                    "command": " ".join(cmd),
                    "ok": True,
                    "dry_run": True,
                    "output": "dry-run",
                }
            )
            continue

        if step == "write_resolved_dropin" and "path" in item and "content" in item:
            ok_dir, out_dir, err_dir = _run_text_command(cmd, timeout=10)
            if not ok_dir:
                results.append(
                    {
                        "step": step,
                        "description": item.get("description", ""),
                        "command": " ".join(cmd),
                        "ok": False,
                        "dry_run": False,
                        "output": (err_dir or out_dir).strip(),
                    }
                )
                continue
            try:
                proc = subprocess.run(
                    ["sudo", "tee", str(item["path"])],
                    input=str(item["content"]),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                ok = proc.returncode == 0
                output = (proc.stderr or proc.stdout or "").strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                ok = False
                output = str(exc)
            results.append(
                {
                    "step": step,
                    "description": item.get("description", ""),
                    "command": f"sudo tee {item['path']}",
                    "ok": ok,
                    "dry_run": False,
                    "output": output,
                }
            )
            continue

        ok, stdout, stderr = _run_text_command(cmd, timeout=15)
        results.append(
            {
                "step": step,
                "description": item.get("description", ""),
                "command": " ".join(cmd),
                "ok": ok,
                "dry_run": False,
                "output": (stderr if not ok else stdout).strip(),
            }
        )
    return results


class Plugin(DiagnosticPlugin):
    """Built-in DNS diagnostic plugin for ``fixos dns``, ``fixos auto``, and ``fixos scan``."""

    name = "dns"
    description = (
        "Diagnostyka i naprawa DNS (systemd-resolved, NetworkManager, /etc/resolv.conf)"
    )
    platforms = ["linux"]

    def __init__(
        self,
        probe_hosts: Sequence[str] | None = None,
        upstream_dns: Sequence[str] | None = None,
        fallback_dns: Sequence[str] | None = None,
        resolv_conf_path: Path | None = None,
    ) -> None:
        self.probe_hosts = tuple(probe_hosts or DEFAULT_PROBE_HOSTS)
        self.upstream_dns = tuple(upstream_dns or DEFAULT_UPSTREAM_DNS)
        self.fallback_dns = tuple(fallback_dns or DEFAULT_FALLBACK_DNS)
        self.resolv_conf_path = resolv_conf_path or Path("/etc/resolv.conf")

    def diagnose(self) -> DiagnosticResult:
        started = time.monotonic()
        findings: list[Finding] = []
        raw_data: dict[str, Any] = {}

        resolv_info = self._read_resolv_conf()
        raw_data["resolv_conf"] = resolv_info
        if not resolv_info["nameservers"]:
            findings.append(
                Finding(
                    title="Brak skonfigurowanych serwerów DNS w /etc/resolv.conf",
                    severity=Severity.CRITICAL,
                    description=(
                        f"Plik {self.resolv_conf_path} nie zawiera żadnego wpisu nameserver."
                    ),
                    suggestion="Uruchom deterministyczną naprawę DNS przez `fixos dns --fix`.",
                    command="fixos dns --fix",
                )
            )

        stats = self._read_resolvectl_statistics()
        raw_data["statistics"] = stats
        total_timeouts = stats.get("total_timeouts", 0)
        if total_timeouts >= TIMEOUT_WARNING_THRESHOLD:
            findings.append(
                Finding(
                    title=f"Wysoka liczba timeoutów DNS ({total_timeouts})",
                    severity=Severity.WARNING,
                    description=(
                        "systemd-resolved zarejestrował liczne przekroczenia czasu zapytań DNS, "
                        "co powoduje zawieszanie narzędzi sieciowych (np. gh, pip, curl)."
                    ),
                    suggestion=(
                        "Dodaj niezawodne serwery DNS (1.1.1.1, 8.8.8.8) z zachowaniem "
                        "lokalnej domeny przez `fixos dns --fix`."
                    ),
                    command="fixos dns --fix",
                    data={"total_timeouts": total_timeouts},
                )
            )

        status = self._read_resolvectl_status()
        raw_data["status"] = status
        nm_connections = _active_nm_connections_by_device()
        raw_data["nm_connections"] = nm_connections

        router_only_links = [
            link
            for link in status.get("links", [])
            if link.get("default_route")
            and link.get("dns_servers")
            and all(is_private_ipv4(s) for s in link["dns_servers"])
        ]
        if router_only_links:
            devices = ", ".join(link["device"] for link in router_only_links)
            servers = ", ".join(
                sorted({s for link in router_only_links for s in link["dns_servers"]})
            )
            severity = (
                Severity.WARNING
                if total_timeouts >= TIMEOUT_WARNING_THRESHOLD
                or len(router_only_links) > 1
                else Severity.INFO
            )
            findings.append(
                Finding(
                    title=f"Interfejsy domyślne używają wyłącznie prywatnego DNS routera ({devices})",
                    severity=severity,
                    description=(
                        f"Aktywne łącza ({devices}) kierują wszystkie zapytania DNS wyłącznie "
                        f"do lokalnego routera ({servers}) bez publicznego zapasu."
                    ),
                    suggestion=(
                        "Skonfiguruj 1.1.1.1 i 8.8.8.8 przed DNS routera, zachowując "
                        "rozwiązywanie domeny lokalnej: `fixos dns --fix`."
                    ),
                    command="fixos dns --fix",
                    data={"devices": [link["device"] for link in router_only_links]},
                )
            )

        probes = self._probe_hosts()
        raw_data["probes"] = probes
        for probe in probes:
            if not probe["ok"]:
                findings.append(
                    Finding(
                        title=f"Nie można rozwiązać nazwy DNS: {probe['host']}",
                        severity=Severity.CRITICAL,
                        description=f"Błąd rozwiązywania nazwy {probe['host']}: {probe['error']}",
                        suggestion="Uruchom `fixos dns --fix` aby odświeżyć i naprawić konfigurację DNS.",
                        command="fixos dns --fix",
                        data=probe,
                    )
                )
            elif probe["latency_ms"] >= LATENCY_WARNING_MS:
                findings.append(
                    Finding(
                        title=(
                            f"Wolne rozwiązywanie DNS dla {probe['host']} "
                            f"({probe['latency_ms']:.0f} ms)"
                        ),
                        severity=Severity.WARNING,
                        description=(
                            f"Zapytanie DNS dla {probe['host']} trwało {probe['latency_ms']:.0f} ms "
                            f"(próg ostrzeżenia: {LATENCY_WARNING_MS:.0f} ms)."
                        ),
                        suggestion="Przełącz DNS na 1.1.1.1 / 8.8.8.8 przez `fixos dns --fix`.",
                        command="fixos dns --fix",
                        data=probe,
                    )
                )

        repair_plan = build_repair_plan(
            status=status,
            nm_connections=nm_connections,
            upstream_dns=self.upstream_dns,
            fallback_dns=self.fallback_dns,
        )
        raw_data["repair_plan"] = [
            {
                "step": item["step"],
                "description": item["description"],
                "command": " ".join(item["command"]),
            }
            for item in repair_plan
        ]

        overall = Severity.OK
        if any(f.severity == Severity.CRITICAL for f in findings):
            overall = Severity.CRITICAL
        elif any(f.severity == Severity.WARNING for f in findings):
            overall = Severity.WARNING
        elif any(f.severity == Severity.INFO for f in findings):
            overall = Severity.INFO

        if not findings:
            findings.append(
                Finding(
                    title="DNS działa poprawnie",
                    severity=Severity.OK,
                    description=(
                        f"Rozwiązywanie nazw ({', '.join(self.probe_hosts)}) działa szybko i bez błędów."
                    ),
                )
            )

        return DiagnosticResult(
            plugin_name=self.name,
            status=overall,
            findings=findings,
            raw_data=raw_data,
            duration_ms=round((time.monotonic() - started) * 1000.0, 2),
        )

    def _read_resolv_conf(self) -> dict[str, list[str]]:
        try:
            content = self.resolv_conf_path.read_text(encoding="utf-8")
        except OSError:
            return {"nameservers": [], "search_domains": [], "options": []}
        return parse_resolv_conf(content)

    def _read_resolvectl_statistics(self) -> dict[str, int]:
        if not shutil.which("resolvectl"):
            return {}
        ok, stdout, _ = _run_text_command(["resolvectl", "statistics"], timeout=5)
        return parse_resolvectl_statistics(stdout) if ok else {}

    def _read_resolvectl_status(self) -> dict[str, Any]:
        if not shutil.which("resolvectl"):
            return {"global_dns": [], "fallback_dns": [], "links": []}
        ok, stdout, _ = _run_text_command(["resolvectl", "status"], timeout=5)
        return (
            parse_resolvectl_status(stdout)
            if ok
            else {"global_dns": [], "fallback_dns": [], "links": []}
        )

    def _probe_hosts(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for host in self.probe_hosts:
            t0 = time.monotonic()
            try:
                infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
                addresses = sorted({info[4][0] for info in infos})
                results.append(
                    {
                        "host": host,
                        "ok": bool(addresses),
                        "addresses": addresses,
                        "latency_ms": latency_ms,
                        "error": None,
                    }
                )
            except OSError as exc:
                latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
                results.append(
                    {
                        "host": host,
                        "ok": False,
                        "addresses": [],
                        "latency_ms": latency_ms,
                        "error": str(exc),
                    }
                )
        return results
