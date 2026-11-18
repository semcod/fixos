"""Mesh network diagnostic plugin — multi-vantage host & printer testing.

Tests reachability and network services of one or more target hosts from every
vantage point available in the local/LAN/SSH mesh:

* every local non-container IPv4 interface (binding ``source_address`` per NIC
  to catch multi-homed / split-subnet / missing-gateway failures);
* discovered or explicit peer devices (ARP/neighbor table, mDNS workstations,
  Tailscale peers, ``~/.ssh/config`` aliases, ``--node``), executing bounded
  non-interactive ``ssh -o BatchMode=yes`` probes directly on reachable peers
  and recording honest passive status when SSH keys are unavailable;
* target-side protocol diagnostics: unicast vs multicast mDNS (UDP 5353) to
  detect IGMP snooping / Wi-Fi multicast isolation, plus read-only SNMPv1
  MIB-II routing inspection to detect a missing default gateway (``0.0.0.0``).
"""

from __future__ import annotations

import base64
import ipaddress
import json
import os
import platform
import re
import shlex
import socket
import struct
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from fixos.platform_utils import run_command
from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Finding, Severity
from fixos.plugins.builtin.printers import (
    PrinterQueue,
    parse_lpstat_v,
    parse_neighbors,
)

Runner = Callable[..., tuple[bool, str, str, int]]

DEFAULT_TARGET_PORTS: tuple[int, ...] = (631, 9100, 515, 80, 443)
MDNS_PORT = 5353
SNMP_PORT = 161
SSH_PORT = 22
MDNS_MULTICAST_ADDR = str(ipaddress.IPv4Address(bytes((224, 0, 0, 251))))
UNSPECIFIED_IPV4 = str(ipaddress.IPv4Address(0))
_SAFE_SSH_TARGET_RE = re.compile(r"^(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9][A-Za-z0-9._-]{0,252}$")

VIRTUAL_IFACE_PREFIXES = (
    "lo",
    "docker",
    "br-",
    "veth",
    "virbr",
    "cni",
    "flannel",
    "cali",
    "podman",
    "lxcbr",
)
IGNORED_SSH_HOSTS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "ssh.dev.azure.com",
    "codeberg.org",
}

REMOTE_PYTHON_PROBE = """
import json, socket, struct, sys, time
args = sys.argv[1:]
if args and args[0] == "--":
    args = args[1:]
target = args[0]
ports = [int(p) for p in args[1].split(",") if p]
target_ip_hint = args[2] if len(args) > 2 and args[2] else None
out = {
    "hostname": socket.gethostname(),
    "source_ip": "",
    "resolved_ip": None,
    "open_ports": [],
    "closed_ports": [],
    "latency_ms": None,
    "mdns_unicast_ok": None,
    "mdns_multicast_ok": None,
}
try:
    out["resolved_ip"] = socket.getaddrinfo(target, None, socket.AF_INET)[0][4][0]
except OSError:
    out["resolved_ip"] = None
connect_host = out["resolved_ip"] or target_ip_hint
if connect_host:
    try:
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.connect((connect_host, 9))
        out["source_ip"] = udp.getsockname()[0]
        udp.close()
    except OSError:
        pass
    latencies = []
    for port in ports:
        t0 = time.monotonic()
        try:
            with socket.create_connection((connect_host, port), timeout=1.2):
                out["open_ports"].append(port)
                latencies.append((time.monotonic() - t0) * 1000.0)
        except OSError:
            out["closed_ports"].append(port)
    if latencies:
        out["latency_ms"] = round(min(latencies), 2)
    pkt = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
    for lbl in ("_services", "_dns-sd", "_udp", "local"):
        pkt += bytes([len(lbl)]) + lbl.encode()
    pkt += struct.pack(">BHH", 0, 12, 0x8001)
    for mcast, key in ((False, "mdns_unicast_ok"), (True, "mdns_multicast_ok")):
        ms = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ms.settimeout(0.7)
        try:
            dest = ("224.0.0.251" if mcast else connect_host, 5353)
            ms.sendto(pkt, dest)
            ok_mdns = False
            end = time.monotonic() + 0.7
            while time.monotonic() < end:
                _, addr = ms.recvfrom(2048)
                if addr[0] == connect_host:
                    ok_mdns = True
                    break
            out[key] = ok_mdns
        except OSError:
            out[key] = False
        finally:
            ms.close()
print(json.dumps(out))
""".strip()


@dataclass
class LocalInterface:
    """Non-loopback IPv4 interface on the coordinator host."""

    name: str
    ip: str
    prefix_len: int = 24

    @property
    def network(self) -> ipaddress.IPv4Network:
        return ipaddress.ip_network(f"{self.ip}/{self.prefix_len}", strict=False)


@dataclass
class MeshNode:
    """A vantage point in the diagnostic mesh (local NIC, SSH host, or LAN peer)."""

    node_id: str
    kind: str  # "local" | "ssh" | "lan"
    address: str
    label: str = ""
    prefix_len: int = 24
    ssh_target: str | None = None
    explicit: bool = False


@dataclass
class NodeProbeResult:
    """Result of probing a target host from one mesh node."""

    node_id: str
    node_kind: str
    source_ip: str
    mode: str  # "active" | "passive"
    resolved_ip: str | None = None
    ping_ok: bool | None = None
    open_ports: list[int] = field(default_factory=list)
    closed_ports: list[int] = field(default_factory=list)
    latency_ms: float | None = None
    mdns_unicast_ok: bool | None = None
    mdns_multicast_ok: bool | None = None
    same_subnet: bool | None = None
    explicit: bool = False
    remote_hostname: str = ""
    note: str = ""

    @property
    def reachable(self) -> bool:
        if self.open_ports or self.closed_ports:
            return bool(self.open_ports)
        return bool(self.ping_ok)


@dataclass
class TargetSnmpInfo:
    """Read-only MIB-II routing and interface metadata read from a target host."""

    sys_descr: str = ""
    netmask: str = ""
    default_gateway: str | None = None
    interfaces: list[dict[str, Any]] = field(default_factory=list)


def is_virtual_interface(name: str) -> bool:
    lowered = name.lower()
    return any(lowered == p or lowered.startswith(p) for p in VIRTUAL_IFACE_PREFIXES)


def parse_ip_j_addr(text: str, include_virtual: bool = False) -> list[LocalInterface]:
    """Parse ``ip -j -4 addr show`` output into ``LocalInterface`` records."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    interfaces: list[LocalInterface] = []
    seen: set[tuple[str, str]] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        ifname = str(item.get("ifname") or "")
        if not ifname or ifname == "lo":
            continue
        if not include_virtual and is_virtual_interface(ifname):
            continue
        operstate = str(item.get("operstate") or "UP").upper()
        if operstate == "DOWN":
            continue
        for addr in item.get("addr_info") or []:
            if not isinstance(addr, dict) or addr.get("family") != "inet":
                continue
            local = str(addr.get("local") or "")
            if not _is_valid_ipv4(local) or local.startswith("127."):
                continue
            prefix = int(addr.get("prefixlen") or 24)
            key = (ifname, local)
            if key not in seen:
                seen.add(key)
                interfaces.append(LocalInterface(name=ifname, ip=local, prefix_len=prefix))
    return interfaces


def parse_ifconfig_text(
    text: str, include_virtual: bool = False
) -> list[LocalInterface]:
    """Fallback parser for macOS ``ifconfig`` / POSIX ``ip -o -4 addr``."""
    interfaces: list[LocalInterface] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        ip_o = re.match(r"^\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if ip_o:
            name, ip, prefix = ip_o.group(1), ip_o.group(2), int(ip_o.group(3))
            if (
                (include_virtual or not is_virtual_interface(name))
                and not ip.startswith("127.")
                and (name, ip) not in seen
            ):
                seen.add((name, ip))
                interfaces.append(LocalInterface(name=name, ip=ip, prefix_len=prefix))
    if interfaces:
        return interfaces

    current = "net0"
    for line in text.splitlines():
        header = re.match(r"^([a-zA-Z0-9_.-]+):\s", line)
        if header:
            current = header.group(1)
            continue
        inet_match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)", line)
        if inet_match:
            ip = inet_match.group(1)
            if ip.startswith("127.") or (not include_virtual and is_virtual_interface(current)):
                continue
            if (current, ip) not in seen:
                seen.add((current, ip))
                interfaces.append(LocalInterface(name=current, ip=ip, prefix_len=24))
    return interfaces


def parse_ssh_config_hosts(text: str) -> list[str]:
    """Extract concrete SSH host aliases from ``~/.ssh/config`` content."""
    aliases: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line.lower().startswith("host "):
            continue
        for token in line.split()[1:]:
            lower = token.lower()
            if (
                any(ch in token for ch in ("*", "?", "!"))
                or lower in IGNORED_SSH_HOSTS
                or lower in {"localhost"}
            ):
                continue
            if token not in seen:
                seen.add(token)
                aliases.append(token)
    return aliases


def parse_tailscale_peers(text: str) -> list[MeshNode]:
    """Parse ``tailscale status --json`` online peers."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    peers = data.get("Peer")
    if not isinstance(peers, dict):
        return []
    nodes: list[MeshNode] = []
    for entry in peers.values():
        if not isinstance(entry, dict) or not entry.get("Online"):
            continue
        ips = entry.get("TailscaleIPs") or []
        ipv4 = next((ip for ip in ips if isinstance(ip, str) and _is_valid_ipv4(ip)), None)
        if not ipv4:
            continue
        host = str(entry.get("HostName") or ipv4)
        nodes.append(
            MeshNode(
                node_id=f"tailscale:{host}@{ipv4}",
                kind="lan",
                address=ipv4,
                label=host,
                prefix_len=32,
                ssh_target=ipv4,
            )
        )
    return nodes


def build_mdns_query(name: str, qtype: int = 12, unicast_response: bool = False) -> bytes:
    """Build a minimal RFC 6762 DNS/mDNS query packet."""
    pkt = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
    for label in name.strip(".").split("."):
        encoded = label.encode("utf-8", errors="ignore")
        pkt += struct.pack("B", len(encoded)) + encoded
    qclass = 0x8001 if unicast_response else 0x0001
    return pkt + b"\x00" + struct.pack(">HH", qtype, qclass)


def extract_printable_labels(packet: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in packet)


class Plugin(DiagnosticPlugin):
    """Multi-vantage mesh host & printer network diagnostics."""

    name = "mesh"
    description = "Diagnostyka sieci mesh (osiągalność hosta z każdego interfejsu i węzła)"
    platforms: ClassVar[list[str]] = ["linux", "macos", "windows"]

    def __init__(
        self,
        targets: list[str] | None = None,
        nodes: list[str] | None = None,
        ports: tuple[int, ...] | list[int] | None = None,
        discover_peers: bool = False,
        probe_ssh: bool = False,
        include_virtual_interfaces: bool = False,
        runner: Runner | None = None,
        resolver: Callable[[str], str | None] | None = None,
        tcp_probe: Callable[[str, int, str | None, float], tuple[bool, float | None]] | None = None,
        mdns_probe: Callable[[str, str | None, bool], bool] | None = None,
        mdns_peer_scan: Callable[[str], dict[str, str]] | None = None,
        snmp_inspector: Callable[[str], TargetSnmpInfo | None] | None = None,
        ssh_config_reader: Callable[[], str] | None = None,
        system: str | None = None,
    ) -> None:
        self._targets = [t.strip() for t in (targets or []) if t and t.strip()]
        self._explicit_nodes = [n.strip() for n in (nodes or []) if n and n.strip()]
        self._ports = tuple(ports) if ports else DEFAULT_TARGET_PORTS
        self._discover_peers = discover_peers
        self._probe_ssh = probe_ssh
        self._include_virtual = include_virtual_interfaces
        self._run = runner or run_command
        self._resolve = resolver or _resolve_ipv4
        self._tcp_probe = tcp_probe or _tcp_connect_from
        self._mdns_probe = mdns_probe or _probe_mdns
        self._mdns_peer_scan = mdns_peer_scan or _scan_mdns_workstations
        self._snmp_inspector = snmp_inspector or _inspect_snmp_mib2
        self._ssh_config_reader = ssh_config_reader or _read_user_ssh_config
        self._system = (system or platform.system()).lower()

    def diagnose(self) -> DiagnosticResult:
        started = time.monotonic()
        findings: list[Finding] = []

        interfaces = self._local_interfaces()
        targets = list(self._targets) or self._default_printer_targets()
        raw: dict[str, Any] = {
            "system": self._system,
            "ports": list(self._ports),
            "local_interfaces": [asdict(i) for i in interfaces],
            "targets": [],
        }

        if not targets:
            findings.append(
                Finding(
                    title="Brak hostów docelowych do testu mesh",
                    severity=Severity.INFO,
                    description=(
                        "Nie podano adresu hosta ani nie wykryto sieciowej kolejki "
                        "drukarki w systemie."
                    ),
                    suggestion="Uruchom `fixos mesh <adres-hosta>` (np. adres IP drukarki).",
                )
            )
            return DiagnosticResult(
                plugin_name=self.name,
                status=Severity.INFO,
                findings=findings,
                raw_data=raw,
                duration_ms=(time.monotonic() - started) * 1000,
            )

        resolved_targets = {t: self._resolve_target(t) for t in targets}
        target_ips = {ip for ip in resolved_targets.values() if ip}
        mesh_nodes = self._build_mesh_nodes(interfaces, target_ips)
        raw["mesh_nodes"] = [asdict(n) for n in mesh_nodes]

        for target in targets:
            target_ip = resolved_targets.get(target)
            target_report = self._diagnose_single_target(
                target=target,
                target_ip=target_ip,
                interfaces=interfaces,
                mesh_nodes=mesh_nodes,
                findings=findings,
            )
            raw["targets"].append(target_report)

        return DiagnosticResult(
            plugin_name=self.name,
            status=_worst(findings),
            findings=findings,
            raw_data=raw,
            duration_ms=(time.monotonic() - started) * 1000,
        )

    # -------------------------------------------------------- target & nodes
    def _default_printer_targets(self) -> list[str]:
        """Discover configured network printer hosts when no target is passed."""
        hosts: list[str] = []
        seen: set[str] = set()
        if self._system == "windows":
            ok, out, _, _ = self._run(
                'powershell -NoProfile -Command "Get-PrinterPort | '
                'ForEach-Object { $_.PrinterHostAddress }"',
                timeout=15,
            )
            if ok:
                for line in out.splitlines():
                    host = line.strip()
                    if host and host not in seen:
                        seen.add(host)
                        hosts.append(host)
            return hosts

        ok, out, _, _ = self._run("LC_ALL=C lpstat -v", timeout=8)
        if not ok:
            return []
        for name, uri in parse_lpstat_v(out).items():
            queue = PrinterQueue(name=name, uri=uri)
            if queue.host and queue.host not in seen:
                seen.add(queue.host)
                hosts.append(queue.host)
        return hosts

    def _local_interfaces(self) -> list[LocalInterface]:
        if self._system == "linux":
            ok, out, _, _ = self._run("ip -j -4 addr show", timeout=5)
            if ok and out:
                parsed = parse_ip_j_addr(out, include_virtual=self._include_virtual)
                if parsed:
                    return parsed
            ok, out, _, _ = self._run("ip -o -4 addr show", timeout=5)
            if ok and out:
                parsed = parse_ifconfig_text(out, include_virtual=self._include_virtual)
                if parsed:
                    return parsed
        elif self._system in {"darwin", "macos"}:
            ok, out, _, _ = self._run("ifconfig", timeout=5)
            if ok and out:
                parsed = parse_ifconfig_text(out, include_virtual=self._include_virtual)
                if parsed:
                    return parsed
        elif self._system == "windows":
            ok, out, _, _ = self._run(
                'powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 '
                "| Select-Object InterfaceAlias,IPAddress,PrefixLength "
                '| ConvertTo-Json"',
                timeout=10,
            )
            if ok and out:
                try:
                    items = json.loads(out)
                    if isinstance(items, dict):
                        items = [items]
                    res = []
                    for it in items or []:
                        alias = str(it.get("InterfaceAlias") or "eth")
                        ip = str(it.get("IPAddress") or "")
                        pref = int(it.get("PrefixLength") or 24)
                        if (
                            _is_valid_ipv4(ip)
                            and not ip.startswith("127.")
                            and (self._include_virtual or not is_virtual_interface(alias))
                        ):
                            res.append(LocalInterface(name=alias, ip=ip, prefix_len=pref))
                    if res:
                        return res
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        fallback_ip = _primary_local_ip()
        if fallback_ip:
            return [LocalInterface(name="default", ip=fallback_ip, prefix_len=24)]
        return []

    def _build_mesh_nodes(
        self, interfaces: list[LocalInterface], target_ips: set[str]
    ) -> list[MeshNode]:
        nodes: list[MeshNode] = []
        local_ips = {iface.ip for iface in interfaces}
        seen_addresses: set[str] = set()

        for iface in interfaces:
            nodes.append(
                MeshNode(
                    node_id=f"local:{iface.name}@{iface.ip}",
                    kind="local",
                    address=iface.ip,
                    label=f"{platform.node() or 'localhost'}:{iface.name}",
                    prefix_len=iface.prefix_len,
                )
            )
            seen_addresses.add(iface.ip)

        for raw_node in self._explicit_nodes:
            host_part = raw_node.split("@", 1)[-1]
            resolved = self._resolve(host_part) or host_part
            if resolved in local_ips:
                continue
            nodes.append(
                MeshNode(
                    node_id=f"ssh:{raw_node}",
                    kind="ssh",
                    address=resolved,
                    label=raw_node,
                    ssh_target=raw_node,
                    explicit=True,
                )
            )
            seen_addresses.add(resolved)

        if not self._discover_peers:
            return nodes

        workstations: dict[str, str] = {}
        for iface in interfaces[:3]:
            for ip, label in self._mdns_peer_scan(iface.ip).items():
                workstations.setdefault(ip, label)

        neighbors = self._neighbor_ips(interfaces)
        for peer_ip in sorted(set(neighbors) | set(workstations)):
            if peer_ip in seen_addresses or peer_ip in target_ips or peer_ip in local_ips:
                continue
            label = workstations.get(peer_ip, "")
            prefix_len = _matching_prefix(peer_ip, interfaces)
            nodes.append(
                MeshNode(
                    node_id=f"peer:{label or peer_ip}" + (f"@{peer_ip}" if label else ""),
                    kind="lan",
                    address=peer_ip,
                    label=label or peer_ip,
                    prefix_len=prefix_len,
                    ssh_target=peer_ip,
                )
            )
            seen_addresses.add(peer_ip)

        ok_ts, ts_out, _, _ = self._run("tailscale status --json", timeout=4)
        if ok_ts and ts_out:
            for ts_node in parse_tailscale_peers(ts_out):
                if ts_node.address not in seen_addresses and ts_node.address not in target_ips:
                    nodes.append(ts_node)
                    seen_addresses.add(ts_node.address)

        if self._probe_ssh:
            for alias in parse_ssh_config_hosts(self._ssh_config_reader()):
                resolved = self._resolve(alias)
                if resolved and (resolved in seen_addresses or resolved in target_ips):
                    continue
                key = resolved or alias
                if key in seen_addresses:
                    continue
                nodes.append(
                    MeshNode(
                        node_id=f"ssh:{alias}",
                        kind="ssh",
                        address=resolved or alias,
                        label=alias,
                        ssh_target=alias,
                    )
                )
                seen_addresses.add(key)

        return nodes

    def _neighbor_ips(self, interfaces: list[LocalInterface]) -> list[str]:
        allowed_ifaces = {i.name for i in interfaces}
        if self._system == "linux":
            ok, out, _, _ = self._run("ip -4 neigh show", timeout=5)
            if ok and out:
                ips: list[str] = []
                for line in out.splitlines():
                    if any(bad in line for bad in ("INCOMPLETE", "FAILED")):
                        continue
                    dev_match = re.search(r"\bdev\s+(\S+)", line)
                    if (
                        dev_match
                        and allowed_ifaces
                        and not self._include_virtual
                        and dev_match.group(1) not in allowed_ifaces
                    ):
                        continue
                    ip_match = re.match(r"^(\d+\.\d+\.\d+\.\d+)\b", line)
                    if ip_match and _is_valid_ipv4(ip_match.group(1)):
                        ips.append(ip_match.group(1))
                return ips
        _, out, _, _ = self._run(
            "arp -an" if self._system != "windows" else "arp -a", timeout=8
        )
        return list(parse_neighbors(out).values())

    def _resolve_target(self, target: str) -> str | None:
        if _is_valid_ipv4(target):
            return target
        resolved = self._resolve(target)
        if resolved:
            return resolved
        return None

    # -------------------------------------------------------- target probing
    def _diagnose_single_target(
        self,
        target: str,
        target_ip: str | None,
        interfaces: list[LocalInterface],
        mesh_nodes: list[MeshNode],
        findings: list[Finding],
    ) -> dict[str, Any]:
        workstations_mcast: set[str] = set()
        if self._discover_peers:
            for iface in interfaces[:3]:
                workstations_mcast.update(self._mdns_peer_scan(iface.ip).keys())

        def probe_one(node: MeshNode) -> NodeProbeResult:
            if node.kind == "local":
                return self._probe_from_local_node(node, target, target_ip)
            return self._probe_from_remote_node(
                node, target, target_ip, workstations_mcast
            )

        with ThreadPoolExecutor(max_workers=max(1, min(8, len(mesh_nodes)))) as pool:
            raw_results = list(pool.map(probe_one, mesh_nodes))

        active_hostnames = {
            r.remote_hostname.lower()
            for r in raw_results
            if r.mode == "active" and r.remote_hostname
        }
        node_results = [
            r
            for r in raw_results
            if not (
                r.mode == "passive"
                and not r.explicit
                and r.node_id.startswith("ssh:")
                and r.node_id.split(":", 1)[1].lower() in active_hostnames
            )
        ]

        effective_ip = target_ip or next(
            (r.resolved_ip for r in node_results if r.resolved_ip), None
        )
        snmp_info: TargetSnmpInfo | None = None
        if effective_ip and any(r.reachable for r in node_results if r.mode == "active"):
            snmp_info = self._snmp_inspector(effective_ip)

        findings.extend(
            self._evaluate_findings(
                target=target,
                target_ip=effective_ip,
                node_results=node_results,
                snmp_info=snmp_info,
            )
        )

        return {
            "target": target,
            "resolved_ip": effective_ip,
            "snmp": asdict(snmp_info) if snmp_info else None,
            "results": [asdict(r) for r in node_results],
        }

    def _probe_from_local_node(
        self, node: MeshNode, target: str, target_ip: str | None
    ) -> NodeProbeResult:
        resolved = target_ip or self._resolve(target)
        same_sub = _in_same_subnet(node.address, node.prefix_len, resolved)
        if not resolved:
            return NodeProbeResult(
                node_id=node.node_id,
                node_kind=node.kind,
                source_ip=node.address,
                mode="active",
                resolved_ip=None,
                closed_ports=list(self._ports),
                same_subnet=same_sub,
                note="nie można rozwiązać nazwy hosta",
            )

        open_ports: list[int] = []
        closed_ports: list[int] = []
        latencies: list[float] = []
        for port in self._ports:
            ok, latency = self._tcp_probe(resolved, port, node.address, 1.2)
            if ok:
                open_ports.append(port)
                if latency is not None:
                    latencies.append(latency)
            else:
                closed_ports.append(port)

        ping_ok: bool | None = None
        if not open_ports:
            ping_ok = self._icmp_ping_local(resolved, node.address)

        mdns_ucast = self._mdns_probe(resolved, node.address, False)
        mdns_mcast = self._mdns_probe(resolved, node.address, True)

        return NodeProbeResult(
            node_id=node.node_id,
            node_kind=node.kind,
            source_ip=node.address,
            mode="active",
            resolved_ip=resolved,
            ping_ok=ping_ok,
            open_ports=open_ports,
            closed_ports=closed_ports,
            latency_ms=round(min(latencies), 2) if latencies else None,
            mdns_unicast_ok=mdns_ucast,
            mdns_multicast_ok=mdns_mcast,
            same_subnet=same_sub,
        )

    def _probe_from_remote_node(
        self,
        node: MeshNode,
        target: str,
        target_ip: str | None,
        mcast_responders: set[str],
    ) -> NodeProbeResult:
        same_sub = _in_same_subnet(node.address, node.prefix_len, target_ip)
        should_try_ssh = (self._probe_ssh or node.explicit) and bool(node.ssh_target)

        if should_try_ssh and node.kind == "lan" and _is_valid_ipv4(node.address):
            ssh_open, _ = self._tcp_probe(node.address, SSH_PORT, None, 0.45)
            if not ssh_open:
                should_try_ssh = False

        if should_try_ssh and node.ssh_target:
            remote = self._exec_ssh_probe(node.ssh_target, target, target_ip)
            if remote is not None:
                src_ip = str(remote.get("source_ip") or node.address)
                resolved_remote = remote.get("resolved_ip")
                r_host = str(remote.get("hostname") or "")
                return NodeProbeResult(
                    node_id=node.node_id,
                    node_kind=node.kind,
                    source_ip=src_ip,
                    mode="active",
                    resolved_ip=resolved_remote,
                    open_ports=[int(p) for p in remote.get("open_ports") or []],
                    closed_ports=[int(p) for p in remote.get("closed_ports") or []],
                    latency_ms=remote.get("latency_ms"),
                    mdns_unicast_ok=remote.get("mdns_unicast_ok"),
                    mdns_multicast_ok=remote.get("mdns_multicast_ok"),
                    same_subnet=_in_same_subnet(
                        src_ip, node.prefix_len, resolved_remote or target_ip
                    ),
                    explicit=node.explicit,
                    remote_hostname=r_host,
                    note=f"zdalny test SSH ({r_host or node.ssh_target})",
                )
            if node.explicit:
                return NodeProbeResult(
                    node_id=node.node_id,
                    node_kind=node.kind,
                    source_ip=node.address,
                    mode="passive",
                    resolved_ip=target_ip,
                    same_subnet=same_sub,
                    explicit=True,
                    note="brak dostępu SSH BatchMode do węzła",
                )

        mcast_seen = node.address in mcast_responders if mcast_responders else None
        note_parts = ["węzeł pasywny LAN (brak klucza/usługi SSH)"]
        if mcast_seen is True:
            note_parts.append("widoczny w multicast mDNS")
        return NodeProbeResult(
            node_id=node.node_id,
            node_kind=node.kind,
            source_ip=node.address,
            mode="passive",
            resolved_ip=target_ip,
            mdns_multicast_ok=mcast_seen,
            same_subnet=same_sub,
            explicit=node.explicit,
            note="; ".join(note_parts),
        )

    def _exec_ssh_probe(
        self, ssh_target: str, target: str, target_ip: str | None
    ) -> dict[str, Any] | None:
        if not _SAFE_SSH_TARGET_RE.fullmatch(ssh_target):
            return None
        encoded = base64.b64encode(REMOTE_PYTHON_PROBE.encode("utf-8")).decode("ascii")
        ports_csv = ",".join(str(int(p)) for p in self._ports)
        ip_arg = shlex.quote(target_ip or "")
        remote_cmd = (
            "python3 -c "
            + shlex.quote(
                f"import base64,sys;exec(base64.b64decode('{encoded}').decode())"
            )
            + f" {shlex.quote(target)} {shlex.quote(ports_csv)} {ip_arg}"
        )
        ssh_cmd = (
            "ssh -o BatchMode=yes -o ConnectTimeout=3 "
            "-o StrictHostKeyChecking=accept-new -- "
            f"{shlex.quote(ssh_target)} {shlex.quote(remote_cmd)}"
        )
        ok, out, _, _ = self._run(ssh_cmd, timeout=10)
        if not ok or not out:
            return None
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
        return None

    def _icmp_ping_local(self, target_ip: str, source_ip: str) -> bool:
        if self._system == "windows":
            cmd = f"ping -n 1 -w 1000 -S {shlex.quote(source_ip)} {shlex.quote(target_ip)}"
        elif self._system in {"darwin", "macos"}:
            cmd = f"ping -c 1 -W 1000 -S {shlex.quote(source_ip)} {shlex.quote(target_ip)}"
        else:
            cmd = f"ping -c 1 -W 1 -I {shlex.quote(source_ip)} {shlex.quote(target_ip)}"
        ok, _, _, _ = self._run(cmd, timeout=4)
        return ok

    # -------------------------------------------------------------- findings
    def _evaluate_findings(
        self,
        target: str,
        target_ip: str | None,
        node_results: list[NodeProbeResult],
        snmp_info: TargetSnmpInfo | None,
    ) -> list[Finding]:
        found: list[Finding] = []
        active = [r for r in node_results if r.mode == "active"]
        succeeded = [r for r in active if r.reachable]
        failed = [r for r in active if not r.reachable]

        if not _is_valid_ipv4(target):
            unresolved_nodes = [r.node_id for r in active if r.resolved_ip is None]
            if unresolved_nodes:
                found.append(
                    Finding(
                        title=f"{target}: nazwa hosta nie rozwiązuje się w mesh",
                        severity=Severity.CRITICAL if not target_ip else Severity.WARNING,
                        description=(
                            f"Węzły ({', '.join(unresolved_nodes)}) nie potrafią "
                            f"rozwiązać nazwy '{target}' przez DNS ani mDNS."
                        ),
                        suggestion=(
                            "Użyj stałego adresu IP (rezerwacja DHCP na routerze) "
                            "lub skonfiguruj wpis DNS na routerze."
                        ),
                        data={"target": target, "unresolved_nodes": unresolved_nodes},
                    )
                )

        if active and not succeeded:
            found.append(
                Finding(
                    title=f"{target}: nieosiągalny z żadnego aktywnego węzła mesh ({len(active)})",
                    severity=Severity.CRITICAL,
                    description=(
                        f"Żaden z {len(active)} aktywnych punktów testowych "
                        f"({', '.join(r.node_id for r in active)}) nie uzyskał "
                        f"połączenia z {target}"
                        + (f" ({target_ip})" if target_ip and target_ip != target else "")
                        + f" na portach {list(self._ports)}."
                    ),
                    suggestion=(
                        "Sprawdź zasilanie urządzenia, poprawność adresu IP, "
                        "podsieć Wi-Fi/LAN oraz reguły zapory."
                    ),
                    data={"target": target, "target_ip": target_ip},
                )
            )
            return found

        if succeeded and failed:
            ok_ids = ", ".join(f"{r.node_id}" for r in succeeded)
            fail_ids = ", ".join(f"{r.node_id}" for r in failed)
            has_explicit_fail = any(
                r.node_kind == "ssh" for r in failed
            )
            found.append(
                Finding(
                    title=(
                        f"{target}: częściowa osiągalność w sieci mesh "
                        f"({len(succeeded)}/{len(active)} aktywnych węzłów)"
                    ),
                    severity=Severity.CRITICAL if has_explicit_fail else Severity.WARNING,
                    description=(
                        f"Połączenie działa z: [{ok_ids}], ale zawodzi z: [{fail_ids}]. "
                        "Urządzenia w innej podsieci Wi-Fi/VLAN lub za drugim "
                        "routerem nie mają trasy zwrotnej do hosta."
                    ),
                    suggestion=(
                        "Upewnij się, że Wi-Fi (smartfon/laptop) i host działają w "
                        "jednej podsieci (tryb Access Point/Bridge zamiast podwójnego "
                        "NAT), wyłącz izolację klientów Wi-Fi (AP Isolation) oraz "
                        "ustaw poprawną bramę domyślną na urządzeniu."
                    ),
                    data={
                        "target": target,
                        "succeeded": [r.node_id for r in succeeded],
                        "failed": [r.node_id for r in failed],
                    },
                )
            )

        if snmp_info is not None and snmp_info.default_gateway == UNSPECIFIED_IPV4:
            found.append(
                Finding(
                    title=f"{target}: brak bramy domyślnej na urządzeniu (Gateway = {UNSPECIFIED_IPV4})",
                    severity=Severity.CRITICAL,
                    description=(
                        f"Tablica routingu SNMP hosta {target_ip or target} "
                        f"({snmp_info.sys_descr or 'SNMP MIB-II'}) zwraca "
                        f"Default Gateway = {UNSPECIFIED_IPV4} (maska {snmp_info.netmask or '?'}). "
                        "Urządzenie odrzuca pakiety zwrotne do wszystkich klientów "
                        "spoza własnej podsieci lokalnej (np. z innej podsieci Wi-Fi, "
                        "sieci Gościnnej lub VPN)."
                    ),
                    suggestion=(
                        "W ustawieniach TCP/IP urządzenia włącz DHCP (Auto) albo "
                        "wpisz adres IP routera jako bramę domyślną (Gateway)."
                    ),
                    data={
                        "target": target,
                        "target_ip": target_ip,
                        "default_gateway": snmp_info.default_gateway,
                        "netmask": snmp_info.netmask,
                    },
                )
            )

        ucast_any = any(r.mdns_unicast_ok is True for r in active)
        mcast_any = any(r.mdns_multicast_ok is True for r in active)
        mcast_tested = any(r.mdns_multicast_ok is not None for r in active)
        if ucast_any and mcast_tested and not mcast_any:
            found.append(
                Finding(
                    title=f"{target}: multicast mDNS (Bonjour/AirPrint) jest blokowany w sieci",
                    severity=Severity.WARNING,
                    description=(
                        f"Host {target_ip or target} odpowiada na bezpośrednie zapytania "
                        f"unicast mDNS (UDP {MDNS_PORT}), ale nie odpowiada na multicast "
                        f"mDNS ({MDNS_MULTICAST_ADDR}:{MDNS_PORT}). Automatyczne wykrywanie "
                        "drukarki/usługi na smartfonach (Wi-Fi AirPrint/Mopria) oraz PC "
                        "nie zobaczy tego urządzenia."
                    ),
                    suggestion=(
                        "Dodaj urządzenie ręcznie po adresie IP na telefonie/PC, "
                        "zrestartuj kartę sieciową urządzenia i wyłącz IGMP snooping "
                        "oraz izolację klientów (AP Isolation) na moście LAN/Wi-Fi routera."
                    ),
                    data={
                        "target": target,
                        "target_ip": target_ip,
                        "mdns_unicast_ok": True,
                        "mdns_multicast_ok": False,
                    },
                )
            )

        explicit_passive = [
            r for r in node_results if r.mode == "passive" and r.explicit
        ]
        if explicit_passive:
            ids = ", ".join(r.node_id for r in explicit_passive)
            found.append(
                Finding(
                    title=f"Pominięto aktywny test SSH na węzłach bez autoryzacji kluczem ({len(explicit_passive)})",
                    severity=Severity.INFO,
                    description=(
                        f"Węzły [{ids}] nie przyjęły nieinteraktywnego połączenia "
                        "`ssh -o BatchMode=yes`."
                    ),
                    suggestion="Skonfiguruj klucz SSH (`ssh-copy-id`) dla zdalnych węzłów mesh.",
                    data={"nodes": [r.node_id for r in explicit_passive]},
                )
            )

        return found


# ------------------------------------------------------------ network helpers
def _is_valid_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def _resolve_ipv4(host: str) -> str | None:
    try:
        return socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
    except (socket.gaierror, UnicodeError, IndexError, OSError):
        return None


def _primary_local_ip() -> str | None:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 9))
        local = probe.getsockname()[0]
        probe.close()
        return local
    except OSError:
        return None


def _matching_prefix(ip: str, interfaces: list[LocalInterface]) -> int:
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return 24
    for iface in interfaces:
        if addr in iface.network:
            return iface.prefix_len
    return 24


def _in_same_subnet(
    source_ip: str, prefix_len: int, target_ip: str | None
) -> bool | None:
    if not (_is_valid_ipv4(source_ip) and target_ip and _is_valid_ipv4(target_ip)):
        return None
    net = ipaddress.ip_network(f"{source_ip}/{prefix_len}", strict=False)
    return ipaddress.IPv4Address(target_ip) in net


def _tcp_connect_from(
    host: str, port: int, source_ip: str | None = None, timeout: float = 1.2
) -> tuple[bool, float | None]:
    started = time.monotonic()
    source_addr = (source_ip, 0) if source_ip and _is_valid_ipv4(source_ip) else None
    try:
        with socket.create_connection((host, port), timeout=timeout, source_address=source_addr):
            return True, (time.monotonic() - started) * 1000.0
    except OSError:
        return False, None


def _probe_mdns(
    target_ip: str, source_ip: str | None = None, multicast: bool = False
) -> bool:
    """Test whether ``target_ip`` answers mDNS via unicast or multicast."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(0.9)
    try:
        if source_ip and _is_valid_ipv4(source_ip):
            sock.bind((source_ip, 0))
            if multicast:
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(source_ip),
                )
        query = build_mdns_query(
            "_services._dns-sd._udp.local", qtype=12, unicast_response=True
        )
        dest = (MDNS_MULTICAST_ADDR if multicast else target_ip, MDNS_PORT)
        sock.sendto(query, dest)
        deadline = time.monotonic() + 0.9
        while time.monotonic() < deadline:
            _, addr = sock.recvfrom(4096)
            if addr[0] == target_ip:
                return True
        return False
    except OSError:
        return False
    finally:
        sock.close()


def _scan_mdns_workstations(source_ip: str) -> dict[str, str]:
    """Send one bounded mDNS DNS-SD query to discover active LAN peer labels."""
    peers: dict[str, str] = {}
    if not _is_valid_ipv4(source_ip):
        return peers
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(0.7)
    try:
        sock.bind((source_ip, 0))
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(source_ip)
        )
        for svc in ("_workstation._tcp.local", "_services._dns-sd._udp.local"):
            sock.sendto(
                build_mdns_query(svc, qtype=12, unicast_response=True),
                (MDNS_MULTICAST_ADDR, MDNS_PORT),
            )
        deadline = time.monotonic() + 0.7
        while time.monotonic() < deadline:
            data, addr = sock.recvfrom(4096)
            printable = extract_printable_labels(data)
            ws_match = re.search(
                r"([A-Za-z0-9][A-Za-z0-9_-]{1,31})\s*\[[0-9a-fA-F:]{17}\]",
                printable,
            )
            if ws_match:
                label = ws_match.group(1)
            else:
                tail = printable.rsplit("local", 1)[-1]
                tokens = [
                    tok
                    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,31}", tail)
                    if tok.lower()
                    not in {
                        "local",
                        "tcp",
                        "udp",
                        "services",
                        "dns-sd",
                        "workstation",
                        "smb",
                        "http",
                        "ipp",
                        "printer",
                        "device-info",
                    }
                ]
                label = tokens[0] if tokens else ""
            peers.setdefault(addr[0], label)
    except OSError:
        pass
    finally:
        sock.close()
    return peers


def _read_user_ssh_config() -> str:
    cfg = Path(os.path.expanduser("~")) / ".ssh" / "config"
    try:
        return cfg.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# --------------------------------------------------------- minimal SNMPv1 MIB-2
def _ber_len(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _ber_oid(oid: str) -> bytes:
    nums = [int(part) for part in oid.split(".")]
    out = bytearray([40 * nums[0] + nums[1]])
    for val in nums[2:]:
        if val == 0:
            out.append(0)
        else:
            chunks: list[int] = []
            while val:
                chunks.append(val & 0x7F)
                val >>= 7
            for chunk in reversed(chunks[1:]):
                out.append(chunk | 0x80)
            out.append(chunks[0])
    return b"\x06" + _ber_len(len(out)) + bytes(out)


def _ber_decode_tlv(buf: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    tag = buf[offset]
    offset += 1
    length = buf[offset]
    offset += 1
    if length & 0x80:
        nbytes = length & 0x7F
        length = int.from_bytes(buf[offset : offset + nbytes], "big")
        offset += nbytes
    return tag, buf[offset : offset + length], offset + length


def _ber_decode_oid(raw: bytes) -> str:
    parts = [raw[0] // 40, raw[0] % 40]
    acc = 0
    for byte in raw[1:]:
        acc = (acc << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            parts.append(acc)
            acc = 0
    return ".".join(str(p) for p in parts)


def _snmp_get_value(
    sock: socket.socket, target_ip: str, oid: str, pdu_tag: int = 0xA0, req_id: int = 1
) -> tuple[str, int, bytes] | None:
    oid_bytes = _ber_oid(oid)
    varbind = b"\x30" + _ber_len(len(oid_bytes) + 2) + oid_bytes + b"\x05\x00"
    vbl = b"\x30" + _ber_len(len(varbind)) + varbind
    pdu_body = b"\x02\x01" + bytes([req_id & 0x7F]) + b"\x02\x01\x00\x02\x01\x00" + vbl
    pdu = bytes([pdu_tag]) + _ber_len(len(pdu_body)) + pdu_body
    msg_body = b"\x02\x01\x00\x04\x06public" + pdu
    pkt = b"\x30" + _ber_len(len(msg_body)) + msg_body
    try:
        sock.sendto(pkt, (target_ip, SNMP_PORT))
        resp, _ = sock.recvfrom(4096)
        _, msg, _ = _ber_decode_tlv(resp, 0)
        _, _, pos = _ber_decode_tlv(msg, 0)
        _, _, pos = _ber_decode_tlv(msg, pos)
        _, resp_pdu, _ = _ber_decode_tlv(msg, pos)
        _, _, q = _ber_decode_tlv(resp_pdu, 0)
        _, err_status, q = _ber_decode_tlv(resp_pdu, q)
        if err_status and err_status[0] != 0:
            return None
        _, _, q = _ber_decode_tlv(resp_pdu, q)
        _, resp_vbl, _ = _ber_decode_tlv(resp_pdu, q)
        _, resp_vb, _ = _ber_decode_tlv(resp_vbl, 0)
        _, resp_oid, r = _ber_decode_tlv(resp_vb, 0)
        val_tag, val_bytes, _ = _ber_decode_tlv(resp_vb, r)
        return _ber_decode_oid(resp_oid), val_tag, val_bytes
    except (OSError, IndexError, ValueError):
        return None


def _inspect_snmp_mib2(target_ip: str) -> TargetSnmpInfo | None:
    """Read sysDescr, subnet mask and default gateway via read-only SNMPv1."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.8)
    try:
        descr_res = _snmp_get_value(sock, target_ip, "1.3.6.1.2.1.1.1.0", pdu_tag=0xA0, req_id=1)
        if descr_res is None:
            return None
        info = TargetSnmpInfo(
            sys_descr=descr_res[2].decode("latin1", errors="replace").strip()
        )
        mask_oid = f"1.3.6.1.2.1.4.20.1.3.{target_ip}"
        mask_res = _snmp_get_value(sock, target_ip, mask_oid, pdu_tag=0xA0, req_id=2)
        if mask_res and len(mask_res[2]) == 4:
            info.netmask = ".".join(str(b) for b in mask_res[2])
        gw_oid = f"1.3.6.1.2.1.4.21.1.7.{UNSPECIFIED_IPV4}"
        gw_res = _snmp_get_value(sock, target_ip, gw_oid, pdu_tag=0xA0, req_id=3)
        if gw_res and len(gw_res[2]) == 4:
            info.default_gateway = ".".join(str(b) for b in gw_res[2])
        return info
    finally:
        sock.close()


def _worst(findings: list[Finding]) -> Severity:
    order = [Severity.OK, Severity.INFO, Severity.WARNING, Severity.CRITICAL]
    return max((f.severity for f in findings), key=order.index, default=Severity.OK)
