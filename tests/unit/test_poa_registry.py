"""Unit tests for the canonical POA/MCP capability registry (issue #164 / PLF-21815)."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import click
import pytest
from click.testing import CliRunner

from fixos.cli.main import cli
from fixos.mcp_server import registry_search, task_execute
from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Severity
from fixos.plugins.registry import PluginRegistry
from fixos.poa_registry import (
    CANONICAL_OPERATIONS,
    MCP_REGISTRY_SCHEMA,
    NON_EXPOSED_CAPABILITIES,
    NonExposedCapability,
    export_mcp_registry_v1,
    validate_registry_entries,
    verify_capability_parity,
)

_OP_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_URI_RE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s?#]+$")
_URN_RE = re.compile(
    r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def test_live_cli_and_plugin_capability_parity():
    summary = verify_capability_parity()
    assert summary["discovered_count"] >= 40
    assert summary["registered_count"] + summary["non_exposed_count"] == summary["discovered_count"]
    assert summary["internal_count"] >= 5


def test_parity_detects_unregistered_click_command_and_subcommand():
    group = click.Group("fixos-test")
    for name in sorted(cli.commands):
        group.add_command(cli.commands[name], name=name)

    @click.command("rogue_cmd")
    def rogue_cmd() -> None:
        pass

    group.add_command(rogue_cmd)
    with pytest.raises(ValueError, match=r"UNREGISTERED_PUBLIC_CAPABILITIES.*cli:rogue_cmd"):
        verify_capability_parity(cli_group=group)

    group2 = click.Group("fixos-test-sub")
    for name in sorted(cli.commands):
        if name == "profile":
            sub_group = click.Group("profile")
            for sname, scmd in cli.commands["profile"].commands.items():
                sub_group.add_command(scmd, name=sname)

            @click.command("secret_sub")
            def secret_sub() -> None:
                pass

            sub_group.add_command(secret_sub)
            group2.add_command(sub_group, name="profile")
        else:
            group2.add_command(cli.commands[name], name=name)

    with pytest.raises(ValueError, match=r"UNREGISTERED_PUBLIC_CAPABILITIES.*cli:profile secret_sub"):
        verify_capability_parity(cli_group=group2)


def test_parity_detects_unregistered_diagnostic_plugin():
    class UnlistedPlugin(DiagnosticPlugin):
        name = "unlisted_sensor"
        description = "Unregistered test plugin"

        def diagnose(self) -> DiagnosticResult:
            return DiagnosticResult(plugin_name=self.name, status=Severity.OK)

    reg = PluginRegistry()
    reg._register_builtins()
    reg.register(UnlistedPlugin())

    with pytest.raises(ValueError, match=r"UNREGISTERED_PUBLIC_CAPABILITIES.*plugin:unlisted_sensor"):
        verify_capability_parity(plugin_registry=reg)


def test_parity_rejects_duplicate_and_stale_bindings():
    extra_non_exposed = (*NON_EXPOSED_CAPABILITIES, NonExposedCapability("cli:quick", "hitl_mutation", "dup"))
    with pytest.raises(ValueError, match="DUPLICATE_CAPABILITY_BINDING"):
        verify_capability_parity(non_exposed=extra_non_exposed)

    stale_non_exposed = (
        *NON_EXPOSED_CAPABILITIES,
        NonExposedCapability("cli:nonexistent_ghost", "hitl_mutation", "stale entry"),
    )
    with pytest.raises(ValueError, match="STALE_CAPABILITY_BINDINGS"):
        verify_capability_parity(non_exposed=stale_non_exposed)


def test_separated_identifiers_and_uniqueness_invariants():
    assert len(CANONICAL_OPERATIONS) > 20
    for spec in CANONICAL_OPERATIONS:
        assert _OP_ID_RE.fullmatch(spec.operation_id)
        assert _URI_RE.fullmatch(spec.process_uri)
        assert _URN_RE.fullmatch(spec.resource_urn)
        assert len({spec.operation_id, spec.process_uri, spec.resource_urn}) == 3
        assert spec.owner == "semcod/fixos"
        assert spec.availability_reason

    dup_id = (CANONICAL_OPERATIONS[0], replace(CANONICAL_OPERATIONS[1], operation_id=CANONICAL_OPERATIONS[0].operation_id))
    with pytest.raises(ValueError, match="DUPLICATE_OPERATION_ID"):
        validate_registry_entries(dup_id)

    dup_uri = (CANONICAL_OPERATIONS[0], replace(CANONICAL_OPERATIONS[1], process_uri=CANONICAL_OPERATIONS[0].process_uri))
    with pytest.raises(ValueError, match="DUPLICATE_PROCESS_URI"):
        validate_registry_entries(dup_uri)

    bad_reason = (replace(CANONICAL_OPERATIONS[0], availability_reason="   "),)
    with pytest.raises(ValueError, match="MISSING_AVAILABILITY_REASON"):
        validate_registry_entries(bad_reason)


def test_freshness_validation_rejects_expired_registry():
    ref_now = datetime(2026, 11, 18, 17, 0, 0, tzinfo=timezone.utc)
    past = (ref_now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    with pytest.raises(ValueError, match="REGISTRY_EXPIRED"):
        validate_registry_entries(CANONICAL_OPERATIONS, expires_at=past, now=ref_now)
    with pytest.raises(ValueError, match="REGISTRY_EXPIRED"):
        export_mcp_registry_v1(now=ref_now, ttl_seconds=0)


def test_mcp_registry_v1_strict_schema_conformance():
    ref_now = datetime(2026, 11, 18, 17, 0, 0, tzinfo=timezone.utc)
    doc = export_mcp_registry_v1(now=ref_now, ttl_seconds=3600)
    assert set(doc.keys()) == {"schema", "revision", "expiresAt", "operations"}
    assert doc["schema"] == MCP_REGISTRY_SCHEMA
    assert doc["expiresAt"] == "2026-11-18T18:00:00Z"
    assert 1 <= len(doc["operations"]) <= 128

    allowed_op_keys = {
        "id",
        "uri",
        "description",
        "owner",
        "effect",
        "available",
        "unavailableReason",
        "deploymentRevision",
        "inputSchema",
        "outputSchema",
    }
    required_op_keys = allowed_op_keys - {"unavailableReason"}
    for op in doc["operations"]:
        assert required_op_keys <= set(op.keys()) <= allowed_op_keys
        assert _OP_ID_RE.fullmatch(op["id"])
        assert _URI_RE.fullmatch(op["uri"])
        assert op["effect"] in {"read", "pure", "mutating"}
        if not op["available"]:
            assert op.get("unavailableReason")

    strict_search = registry_search(query="printers", strict_v1=True, now=ref_now)
    assert set(strict_search.keys()) == {"schema", "revision", "expiresAt", "operations"}
    assert any(op["id"] == "diagnostics_printers" for op in strict_search["operations"])


def test_task_execute_supports_stable_id_and_blocks_unavailable_or_expired(monkeypatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda: {"os": "Linux"},
    )
    by_stable_id = task_execute("diagnostics_quick")
    assert by_stable_id["operation_id"] == "fixos://diagnostics/quick"

    with pytest.raises(ValueError, match="OPERATION_UNAVAILABLE"):
        task_execute("diagnostics_printers")

    import fixos.mcp_server as server

    expired_entry = {
        **dict(server.OPERATIONS_CATALOG[0]),
        "expiresAt": "2020-01-01T00:00:00Z",
    }
    monkeypatch.setattr(server, "OPERATIONS_CATALOG", (expired_entry,))
    with pytest.raises(ValueError, match="REGISTRY_EXPIRED"):
        task_execute("diagnostics_quick")


def test_cli_mcp_registry_v1_flag():
    runner = CliRunner()
    res = runner.invoke(cli, ["mcp", "--registry-v1"])
    assert res.exit_code == 0
    doc = json.loads(res.output)
    assert doc["schema"] == MCP_REGISTRY_SCHEMA
    assert len(doc["operations"]) == len(CANONICAL_OPERATIONS)
