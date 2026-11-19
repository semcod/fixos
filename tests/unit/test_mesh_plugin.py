from __future__ import annotations

import json
import subprocess
import sys

import click
import pytest
from click.testing import CliRunner

from fixos.cli.mesh_cmd import mesh as mesh_cmd
from fixos.cli.mesh_cmd import parse_ports
from fixos.cli.printers_cmd import printers as printers_cmd
from fixos.plugins.base import Severity
from fixos.plugins.builtin.mesh import (
    REMOTE_POSIX_SH_PROBE,
    REMOTE_PYTHON_PROBE,
    Plugin,
    TargetSnmpInfo,
    _ber_decode_oid,
    _ber_decode_tlv,
    _ber_oid,
    build_mdns_query,
    parse_ifconfig_text,
    parse_ip_j_addr,
    parse_posix_probe_output,
    parse_ssh_config_hosts,
    parse_tailscale_peers,
)

IP_J_OUT = json.dumps(
    [
        {
            "ifname": "lo",
            "operstate": "UNKNOWN",
            "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}],
        },
        {
            "ifname": "enp90s0",
            "operstate": "UP",
            "addr_info": [
                {"family": "inet", "local": "192.168.188.212", "prefixlen": 24},
                {"family": "inet", "local": "192.168.1.100", "prefixlen": 24},
            ],
        },
        {
            "ifname": "docker0",
            "operstate": "UP",
            "addr_info": [{"family": "inet", "local": "10.64.0.1", "prefixlen": 24}],
        },
        {
            "ifname": "wlan0",
            "operstate": "DOWN",
            "addr_info": [{"family": "inet", "local": "192.168.188.99", "prefixlen": 24}],
        },
    ]
)


def make_runner(responses: dict[str, str], calls: list[str] | None = None):
    def run(cmd: str, timeout: int = 120):
        if calls is not None:
            calls.append(cmd)
        for key, value in responses.items():
            if key in cmd:
                if value == "__FAIL__":
                    return False, "", "failed", 1
                return True, value, "", 0
        return True, "", "", 0

    return run


def test_parse_ip_j_addr_filters_virtual_and_down_interfaces():
    ifaces = parse_ip_j_addr(IP_J_OUT, include_virtual=False)
    assert [(i.name, i.ip, i.prefix_len) for i in ifaces] == [
        ("enp90s0", "192.168.188.212", 24),
        ("enp90s0", "192.168.1.100", 24),
    ]
    with_virt = parse_ip_j_addr(IP_J_OUT, include_virtual=True)
    assert ("docker0", "10.64.0.1") in [(i.name, i.ip) for i in with_virt]


def test_parse_ifconfig_text_supports_ip_o_and_bsd_ifconfig():
    ip_o = "2: eth0    inet 192.168.10.5/24 brd 192.168.10.255\n5: docker0    inet 172.17.0.1/16\n"
    parsed = parse_ifconfig_text(ip_o)
    assert [(i.name, i.ip, i.prefix_len) for i in parsed] == [("eth0", "192.168.10.5", 24)]

    bsd = "en0: flags=8863<UP>\n\tinet 192.168.10.8 netmask 0xffffff00\nlo0: flags=8049<UP>\n\tinet 127.0.0.1\n"
    parsed_bsd = parse_ifconfig_text(bsd)
    assert [(i.name, i.ip) for i in parsed_bsd] == [("en0", "192.168.10.8")]


def test_parse_ssh_config_and_tailscale_peers():
    ssh_cfg = """
    Host github.com
      User git
    Host !github.com *
      ForwardAgent no
    Host minis maskfleet
      User tom
    """
    assert parse_ssh_config_hosts(ssh_cfg) == ["minis", "maskfleet"]

    calls: list[str] = []
    plugin = Plugin(
        targets=["192.168.188.158"],
        nodes=["-oProxyCommand=evil"],
        probe_ssh=True,
        runner=make_runner({}, calls),
        resolver=lambda h: "192.168.188.55",
        tcp_probe=lambda *a: (False, None),
        mdns_probe=lambda *a: False,
        snmp_inspector=lambda *a: None,
        system="linux",
    )
    plugin.diagnose()
    assert not any("ProxyCommand" in c for c in calls)

    ts = json.dumps(
        {
            "Peer": {
                "k1": {"HostName": "laptop-wifi", "Online": True, "TailscaleIPs": ["100.64.0.12"]},
                "k2": {"HostName": "offline-box", "Online": False, "TailscaleIPs": ["100.64.0.13"]},
            }
        }
    )
    peers = parse_tailscale_peers(ts)
    assert len(peers) == 1
    assert peers[0].label == "laptop-wifi"
    assert peers[0].address == "100.64.0.12"


def test_mdns_packet_and_snmp_oid_roundtrip():
    pkt = build_mdns_query("_ipp._tcp.local", qtype=12, unicast_response=True)
    assert b"\x04_ipp\x04_tcp\x05local\x00" in pkt
    encoded = _ber_oid("1.3.6.1.2.1.4.21.1.7.0.0.0.0")
    tag, raw, _ = _ber_decode_tlv(encoded, 0)
    assert tag == 0x06
    assert _ber_decode_oid(raw) == "1.3.6.1.2.1.4.21.1.7.0.0.0.0"


def test_mesh_detects_partial_reachability_missing_gateway_and_blocked_multicast_mdns():
    responses = {
        "ip -j -4 addr show": IP_J_OUT,
        "ip -4 neigh show": (
            "192.168.188.1 dev enp90s0 lladdr 94:83:c4:eb:73:28 REACHABLE\n"
            "192.168.188.108 dev enp90s0 lladdr 88:a2:9e:97:10:a1 REACHABLE\n"
            "192.168.188.158 dev enp90s0 lladdr 3c:2a:f4:e8:c6:f8 REACHABLE\n"
        ),
        "tailscale status --json": "__FAIL__",
        "ping ": "__FAIL__",
        "ssh -o BatchMode=yes": json.dumps(
            {
                "hostname": "maskfleet",
                "source_ip": "192.168.188.108",
                "resolved_ip": "192.168.188.158",
                "open_ports": [631, 9100],
                "closed_ports": [515],
                "latency_ms": 1.8,
                "mdns_unicast_ok": True,
            }
        ),
    }

    def tcp_probe(host: str, port: int, source_ip: str | None = None, timeout: float = 1.0):
        # SSH port open only on 192.168.188.108 (not on router .1)
        if port == 22:
            return (host == "192.168.188.108"), 0.9
        # Printer reachable from 192.168.188.212, unreachable from secondary 192.168.1.100
        if host == "192.168.188.158" and source_ip == "192.168.188.212" and port in (631, 9100):
            return True, 2.1
        return False, None

    def mdns_probe(target_ip: str, source_ip: str | None = None, multicast: bool = False) -> bool:
        return bool(source_ip == "192.168.188.212" and not multicast)

    plugin = Plugin(
        targets=["192.168.188.158"],
        ports=(631, 9100, 515),
        discover_peers=True,
        probe_ssh=True,
        runner=make_runner(responses),
        resolver=lambda h: h if h.startswith("192.") else None,
        tcp_probe=tcp_probe,
        mdns_probe=mdns_probe,
        mdns_peer_scan=lambda src: {"192.168.188.108": "maskfleet", "192.168.188.1": "GL-MT6000"},
        snmp_inspector=lambda ip: TargetSnmpInfo(
            sys_descr="Brother NC-8900h",
            netmask="255.255.255.0",
            default_gateway="0.0.0.0",
        ),
        ssh_config_reader=lambda: "",
        system="linux",
    )

    result = plugin.diagnose()
    assert result.status == Severity.CRITICAL
    titles = [f.title for f in result.findings]
    assert any("częściowa osiągalność" in t for t in titles)
    assert any("Gateway = 0.0.0.0" in t for t in titles)
    assert any("multicast mDNS" in t for t in titles)

    results_by_id = {
        r["node_id"]: r for r in result.raw_data["targets"][0]["results"]
    }
    assert results_by_id["local:enp90s0@192.168.188.212"]["open_ports"] == [631, 9100]
    assert results_by_id["local:enp90s0@192.168.1.100"]["open_ports"] == []
    assert results_by_id["peer:maskfleet@192.168.188.108"]["mode"] == "active"
    assert results_by_id["peer:maskfleet@192.168.188.108"]["open_ports"] == [631, 9100]
    assert results_by_id["peer:GL-MT6000@192.168.188.1"]["mode"] == "passive"


def test_mesh_reports_total_unreachability_and_explicit_ssh_skip():
    responses = {
        "ip -j -4 addr show": json.dumps(
            [
                {
                    "ifname": "eth0",
                    "operstate": "UP",
                    "addr_info": [{"family": "inet", "local": "192.168.188.212", "prefixlen": 24}],
                }
            ]
        ),
        "ping ": "__FAIL__",
        "ssh -o BatchMode=yes": "__FAIL__",
    }
    plugin = Plugin(
        targets=["BRN3C2AF4E8C6F8.local"],
        nodes=["minis"],
        ports=(631,),
        discover_peers=False,
        probe_ssh=True,
        runner=make_runner(responses),
        resolver=lambda h: "192.168.188.50" if h == "minis" else None,
        tcp_probe=lambda *a: (False, None),
        mdns_probe=lambda *a: False,
        snmp_inspector=lambda *a: None,
        ssh_config_reader=lambda: "",
        system="linux",
    )
    result = plugin.diagnose()
    assert result.status == Severity.CRITICAL
    titles = [f.title for f in result.findings]
    assert any("nazwa hosta nie rozwiązuje się" in t for t in titles)
    assert any("nieosiągalny z żadnego aktywnego węzła" in t for t in titles)


def test_mesh_uses_configured_printer_queues_when_no_target_argument():
    responses = {
        "ip -j -4 addr show": json.dumps(
            [
                {
                    "ifname": "eth0",
                    "operstate": "UP",
                    "addr_info": [{"family": "inet", "local": "192.168.188.212", "prefixlen": 24}],
                }
            ]
        ),
        "lpstat -v": "device for HL: ipp://192.168.188.158/ipp/print",
    }
    plugin = Plugin(
        runner=make_runner(responses),
        resolver=lambda h: h,
        tcp_probe=lambda *a: (True, 1.5),
        mdns_probe=lambda *a: True,
        snmp_inspector=lambda ip: TargetSnmpInfo(
            sys_descr="Printer", netmask="255.255.255.0", default_gateway="192.168.188.1"
        ),
        system="linux",
    )
    result = plugin.diagnose()
    assert result.status == Severity.OK
    assert result.raw_data["targets"][0]["target"] == "192.168.188.158"


def test_cli_mesh_and_printers_mesh_json(monkeypatch):
    assert parse_ports("631, 9100") == (631, 9100)

    def fake_diagnose(self):
        from fixos.plugins.base import DiagnosticResult

        return DiagnosticResult(
            plugin_name="mesh",
            status=Severity.OK,
            findings=[],
            raw_data={
                "mesh_nodes": [{"node_id": "local:eth0@192.168.188.212"}],
                "targets": [
                    {
                        "target": "192.168.188.158",
                        "resolved_ip": "192.168.188.158",
                        "snmp": None,
                        "results": [
                            {
                                "node_id": "local:eth0@192.168.188.212",
                                "mode": "active",
                                "open_ports": [631],
                                "latency_ms": 1.2,
                                "same_subnet": True,
                                "mdns_unicast_ok": True,
                                "mdns_multicast_ok": True,
                            }
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr("fixos.plugins.builtin.mesh.Plugin.diagnose", fake_diagnose)
    runner = CliRunner()
    res = runner.invoke(mesh_cmd, ["192.168.188.158", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["plugin_name"] == "mesh"
    assert data["raw_data"]["targets"][0]["target"] == "192.168.188.158"

    res_text = runner.invoke(mesh_cmd, ["192.168.188.158"])
    assert res_text.exit_code == 0
    assert "Diagnostyka mesh" in res_text.output

    def fake_printer_diagnose(self):
        from fixos.plugins.base import DiagnosticResult

        return DiagnosticResult(
            plugin_name="printers",
            status=Severity.OK,
            findings=[],
            raw_data={
                "queues": [
                    {
                        "name": "HL",
                        "uri": "ipp://192.168.188.158/ipp/print",
                        "address": "192.168.188.158",
                    }
                ]
            },
        )

    monkeypatch.setattr(
        "fixos.plugins.builtin.printers.Plugin.diagnose", fake_printer_diagnose
    )
    res_prn = runner.invoke(printers_cmd, ["--mesh", "--json"])
    assert res_prn.exit_code == 0
    prn_payload = json.loads(res_prn.output)
    assert "mesh" in prn_payload
    assert prn_payload["mesh"]["plugin_name"] == "mesh"


def test_registry_includes_mesh():
    from fixos.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.discover()
    assert "mesh" in registry._plugins


def test_remote_probe_script_and_port_validation_and_usb_queue(monkeypatch):
    with pytest.raises(click.BadParameter):
        parse_ports("631,abc")
    with pytest.raises(click.BadParameter):
        parse_ports("70000")

    proc = subprocess.run(
        [sys.executable, "-c", REMOTE_PYTHON_PROBE, "127.0.0.1", "1", "127.0.0.1"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["resolved_ip"] == "127.0.0.1"
    assert payload["closed_ports"] == [1]

    captured_targets: list[list[str] | None] = []

    def fake_printer_usb(self):
        from fixos.plugins.base import DiagnosticResult

        return DiagnosticResult(
            plugin_name="printers",
            status=Severity.OK,
            findings=[],
            raw_data={
                "queues": [
                    {"name": "USB_HL", "uri": "usb://Brother/HL-L5200DW"},
                    {"name": "IPV6_HL", "uri": "ipp://[fe80::1]:631/ipp/print"},
                ]
            },
        )

    orig_init = Plugin.__init__

    def spy_init(self, *args, **kwargs):
        captured_targets.append(kwargs.get("targets"))
        orig_init(self, *args, **kwargs)

    def fake_mesh_diag(self):
        from fixos.plugins.base import DiagnosticResult

        return DiagnosticResult(
            plugin_name="mesh", status=Severity.OK, findings=[], raw_data={"targets": []}
        )

    monkeypatch.setattr(
        "fixos.plugins.builtin.printers.Plugin.diagnose", fake_printer_usb
    )
    monkeypatch.setattr("fixos.plugins.builtin.mesh.Plugin.__init__", spy_init)
    monkeypatch.setattr("fixos.plugins.builtin.mesh.Plugin.diagnose", fake_mesh_diag)
    res = CliRunner().invoke(printers_cmd, ["--mesh", "--json"])
    assert res.exit_code == 0
    assert captured_targets == [["fe80::1"]]


def test_probe_helpers_validate_ports_and_manage_udp_socket():
    parsed = parse_posix_probe_output(
        "  HOST = router  \n"
        "  OPEN = 631  \n"
        "OPEN=0\n"
        "CLOSED=70000\n"
        "OPEN=²\n"
        "CLOSED=١\n"
        f"OPEN={'9' * 5000}\n"
        f"OPEN={'0' * 5000}1\n"
        "\tCLOSED\t=\t65535\t\n"
    )
    assert parsed is not None
    assert parsed["hostname"] == "router"
    assert parsed["open_ports"] == [631, 1]
    assert parsed["closed_ports"] == [65535]
    assert "with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:" in (
        REMOTE_PYTHON_PROBE
    )


def test_posix_sh_fallback_for_pythonless_ssh_peer_and_non_retry_on_ssh_auth_failure():
    import shutil
    import socket

    # 1. Direct execution of REMOTE_POSIX_SH_PROBE against an ephemeral loopback listener
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(2)
        open_port = srv.getsockname()[1]
        proc = subprocess.run(
            [
                "sh",
                "-c",
                REMOTE_POSIX_SH_PROBE,
                "sh",
                "127.0.0.1",
                "127.0.0.1",
                "127.0.0.1",
                str(open_port),
                "1",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    parsed = parse_posix_probe_output(proc.stdout)
    assert parsed is not None
    assert parsed["resolved_ip"] == "127.0.0.1"
    assert parsed["probe_kind"] == "posix_sh"
    if shutil.which("nc"):
        assert open_port in parsed["open_ports"]
        assert 1 in parsed["closed_ports"]

    # 2. SSH peer missing python3 (rc=127) falls back to POSIX sh probe
    ssh_calls: list[str] = []

    def fallback_runner(cmd: str, timeout: int = 120):
        if "ip -j -4 addr show" in cmd:
            return (
                True,
                json.dumps(
                    [
                        {
                            "ifname": "eth0",
                            "operstate": "UP",
                            "addr_info": [
                                {
                                    "family": "inet",
                                    "local": "192.168.188.212",
                                    "prefixlen": 24,
                                }
                            ],
                        }
                    ]
                ),
                "",
                0,
            )
        if "ssh -o BatchMode=yes" in cmd:
            ssh_calls.append(cmd)
            if "python3 -c" in cmd:
                return False, "", "ash: python3: not found", 127
            return (
                True,
                "HOST=GL-MT6000\nRESOLVED=192.168.188.158\nSRC=192.168.188.1\nOPEN=631\nCLOSED=9100\n",
                "",
                0,
            )
        return True, "", "", 0

    plugin = Plugin(
        targets=["192.168.188.158"],
        nodes=["root@192.168.188.1"],
        ports=(631, 9100),
        discover_peers=False,
        probe_ssh=True,
        runner=fallback_runner,
        resolver=lambda h: h,
        tcp_probe=lambda *a: (True, 1.1),
        mdns_probe=lambda *a: True,
        snmp_inspector=lambda *a: None,
        system="linux",
    )
    res = plugin.diagnose()
    assert len(ssh_calls) == 2
    by_id = {r["node_id"]: r for r in res.raw_data["targets"][0]["results"]}
    router = by_id["ssh:root@192.168.188.1"]
    assert router["mode"] == "active"
    assert router["open_ports"] == [631]
    assert router["closed_ports"] == [9100]
    assert router["remote_hostname"] == "GL-MT6000"
    assert "POSIX sh" in router["note"]

    # 3. Ping-only POSIX sh output (when remote router lacks nc) still marks reachable
    ping_only = parse_posix_probe_output(
        "HOST=openwrt\nRESOLVED=192.168.188.158\nSRC=192.168.188.1\nPING=1\n"
    )
    assert ping_only is not None and ping_only["ping_ok"] is True

    # 4. SSH transport/auth failure (rc=255) does NOT retry, and hostile target is rejected
    auth_calls: list[str] = []

    def auth_fail_runner(cmd: str, timeout: int = 120):
        if "ssh -o BatchMode=yes" in cmd:
            auth_calls.append(cmd)
            return False, "", "Permission denied (publickey).", 255
        return False, "", "", 1

    p_auth = Plugin(
        targets=["192.168.188.158"],
        nodes=["minis"],
        ports=(631,),
        runner=auth_fail_runner,
        resolver=lambda h: "192.168.188.80" if h == "minis" else h,
        tcp_probe=lambda *a: (False, None),
        mdns_probe=lambda *a: False,
        snmp_inspector=lambda *a: None,
        system="linux",
    )
    p_auth.diagnose()
    assert len(auth_calls) == 1
    assert p_auth._exec_ssh_probe("minis", "192.168.1.1;id", None) is None

