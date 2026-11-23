"""Unit tests for the deterministic DNS diagnostic plugin and ``fixos dns`` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from fixos.cli.dns_cmd import dns
from fixos.plugins.base import Severity
from fixos.plugins.builtin.dns import (
    Plugin,
    apply_dns_repair,
    build_repair_plan,
    is_private_ipv4,
    parse_resolv_conf,
    parse_resolvectl_statistics,
    parse_resolvectl_status,
)
from fixos.plugins.registry import PluginRegistry

SAMPLE_STATS_WITH_TIMEOUTS = """
Transactions
                       Current Transactions:       1
                         Total Transactions: 4972893

Cache
                         Current Cache Size:     149
                                 Cache Hits:  167582
                               Cache Misses:  140333

Failure Transactions
                             Total Timeouts:   32239
                    Total Failure Responses:     186
"""

SAMPLE_STATUS_ROUTER_ONLY = """
Global
         Protocols: -LLMNR -mDNS -DNSOverTLS DNSSEC=no/unsupported
  resolv.conf mode: stub

Link 2 (enp90s0)
    Current Scopes: DNS
Current DNS Server: 192.168.188.1
       DNS Servers: 192.168.188.1
        DNS Domain: lan
     Default Route: yes

Link 3 (wlp89s0)
    Current Scopes: DNS
Current DNS Server: 192.168.188.1
       DNS Servers: 192.168.188.1
        DNS Domain: lan
     Default Route: yes
"""


def test_parse_resolv_conf() -> None:
    parsed = parse_resolv_conf(
        "# comment\nnameserver 127.0.0.53\noptions edns0 trust-ad\nsearch lan home.local\n"
    )
    assert parsed["nameservers"] == ["127.0.0.53"]
    assert parsed["search_domains"] == ["lan", "home.local"]
    assert parsed["options"] == ["edns0", "trust-ad"]


def test_parse_resolvectl_statistics() -> None:
    stats = parse_resolvectl_statistics(SAMPLE_STATS_WITH_TIMEOUTS)
    assert stats["total_transactions"] == 4972893
    assert stats["total_timeouts"] == 32239
    assert stats["cache_hits"] == 167582
    assert stats["failure_responses"] == 186


def test_parse_resolvectl_status() -> None:
    status = parse_resolvectl_status(SAMPLE_STATUS_ROUTER_ONLY)
    assert len(status["links"]) == 2
    assert status["links"][0]["device"] == "enp90s0"
    assert status["links"][0]["dns_servers"] == ["192.168.188.1"]
    assert status["links"][0]["default_route"] is True
    assert status["links"][0]["dns_domains"] == ["lan"]


def test_is_private_ipv4() -> None:
    assert is_private_ipv4("192.168.188.1") is True
    assert is_private_ipv4("127.0.0.53") is True
    assert is_private_ipv4("1.1.1.1") is False
    assert is_private_ipv4("8.8.8.8") is False
    assert is_private_ipv4("not-an-ip") is False


def test_build_repair_plan_includes_dropin_and_nmcli() -> None:
    status = parse_resolvectl_status(SAMPLE_STATUS_ROUTER_ONLY)
    plan = build_repair_plan(
        status=status,
        nm_connections={"enp90s0": "Wired connection 1", "wlp89s0": "fritz 1"},
    )
    steps = [item["step"] for item in plan]
    assert "write_resolved_dropin" in steps
    assert "nmcli_dns_enp90s0" in steps
    assert "nmcli_reapply_enp90s0" in steps
    assert "nmcli_dns_wlp89s0" in steps
    assert "restart_resolved" in steps
    assert "flush_dns_cache" in steps

    nm_step = next(item for item in plan if item["step"] == "nmcli_dns_enp90s0")
    assert "1.1.1.1 8.8.8.8 192.168.188.1" in nm_step["command"]
    assert "ipv4.dns-search" in nm_step["command"]


def test_apply_dns_repair_dry_run_skips_subprocess() -> None:
    status = parse_resolvectl_status(SAMPLE_STATUS_ROUTER_ONLY)
    plan = build_repair_plan(status=status, nm_connections={"enp90s0": "Wired"})
    with patch("subprocess.run") as mock_run:
        results = apply_dns_repair(plan, dry_run=True)
    mock_run.assert_not_called()
    assert len(results) == len(plan)
    assert all(r["ok"] and r["dry_run"] for r in results)


def test_plugin_diagnose_flags_timeouts_and_router_only(tmp_path: Path) -> None:
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 127.0.0.53\nsearch lan\n", encoding="utf-8")

    plugin = Plugin(probe_hosts=("api.github.com",), resolv_conf_path=resolv)
    with (
        patch.object(
            plugin,
            "_read_resolvectl_statistics",
            return_value=parse_resolvectl_statistics(SAMPLE_STATS_WITH_TIMEOUTS),
        ),
        patch.object(
            plugin,
            "_read_resolvectl_status",
            return_value=parse_resolvectl_status(SAMPLE_STATUS_ROUTER_ONLY),
        ),
        patch(
            "fixos.plugins.builtin.dns._active_nm_connections_by_device",
            return_value={"enp90s0": "Wired connection 1"},
        ),
        patch(
            "socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("140.82.121.6", 443))],
        ),
    ):
        result = plugin.diagnose()

    assert result.status == Severity.WARNING
    titles = [f.title for f in result.findings]
    assert any("timeoutów DNS" in t for t in titles)
    assert any("prywatnego DNS routera" in t for t in titles)


def test_plugin_diagnose_critical_on_resolution_failure(tmp_path: Path) -> None:
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 127.0.0.53\n", encoding="utf-8")

    plugin = Plugin(probe_hosts=("api.github.com",), resolv_conf_path=resolv)
    with (
        patch.object(plugin, "_read_resolvectl_statistics", return_value={}),
        patch.object(
            plugin,
            "_read_resolvectl_status",
            return_value={"global_dns": ["1.1.1.1"], "fallback_dns": [], "links": []},
        ),
        patch("fixos.plugins.builtin.dns._active_nm_connections_by_device", return_value={}),
        patch("socket.getaddrinfo", side_effect=OSError("Temporary failure in name resolution")),
    ):
        result = plugin.diagnose()

    assert result.status == Severity.CRITICAL
    assert any("Nie można rozwiązać nazwy DNS" in f.title for f in result.findings)


def test_registry_discovers_builtin_dns_plugin() -> None:
    registry = PluginRegistry()
    registry._register_builtins()
    assert "dns" in registry._plugins


def test_cli_dns_json_and_dry_run() -> None:
    runner = CliRunner()
    fake_result = Plugin(probe_hosts=("api.github.com",))
    with (
        patch.object(
            Plugin,
            "diagnose",
            return_value=MagicMock(
                to_dict=lambda: {
                    "plugin_name": "dns",
                    "status": "warning",
                    "findings": [],
                    "raw_data": {},
                    "duration_ms": 5.0,
                },
                raw_data={
                    "status": parse_resolvectl_status(SAMPLE_STATUS_ROUTER_ONLY),
                    "nm_connections": {"enp90s0": "Wired connection 1"},
                },
                status=Severity.WARNING,
                findings=[],
                duration_ms=5.0,
            ),
        ),
    ):
        outcome = runner.invoke(dns, ["--fix", "--dry-run", "--json"])

    assert outcome.exit_code == 0, outcome.output
    payload = json.loads(outcome.output)
    assert payload["plugin_name"] == "dns"
    assert len(payload["repair_results"]) >= 3
    assert all(step["dry_run"] is True for step in payload["repair_results"])
    assert fake_result.name == "dns"
