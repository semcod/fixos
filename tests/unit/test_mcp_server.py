"""Unit tests for the FixOS MCP server and CLI subcommand (wellmanifest/mcp & wellmanifest/nl-dsl-llm)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from fixos.cli.main import cli
from fixos.mcp_server import (
    CATALOG_SCHEMA,
    PLAN_SCHEMA,
    RECEIPT_SCHEMA,
    catalog_digest,
    handle_jsonrpc_message,
    handle_mcp_tool_call,
    mcp_tools_list,
    registry_search,
    serve_stdio,
    task_execute,
    task_plan,
    task_status,
)


def test_registry_search_and_catalog_digest():
    result = registry_search()
    assert result["schema"] == CATALOG_SCHEMA
    assert result["registry_digest"] == catalog_digest()
    assert len(result["registry_digest"]) == 64
    op_ids = {op["operation_id"] for op in result["operations"]}
    assert {
        "fixos://diagnostics/quick",
        "fixos://diagnostics/disk",
        "fixos://diagnostics/projects",
        "fixos://cleanup/auto",
    } <= op_ids

    filtered = registry_search(query="projects")
    assert filtered["count"] >= 1
    assert any(op["operation_id"] == "fixos://diagnostics/projects" for op in filtered["operations"])


def test_task_plan_maps_intents_without_executing():
    clean_plan = task_plan("zwolnij miejsce na dysku automatycznie")
    assert clean_plan["schema"] == PLAN_SCHEMA
    assert clean_plan["advisory"] is True
    assert clean_plan["grants_authority"] is False
    assert clean_plan["executable"] is False
    assert clean_plan["operation_id"] == "fixos://cleanup/auto"
    assert clean_plan["effect"] == "mutate"

    proj_plan = task_plan("sprawdz stare projekty z ostatniego tygodnia")
    assert proj_plan["operation_id"] == "fixos://diagnostics/projects"
    assert proj_plan["effect"] == "read"

    disk_plan = task_plan("pokaz rozmiar cache i wolne miejsce na dysku")
    assert disk_plan["operation_id"] == "fixos://diagnostics/disk"
    assert disk_plan["effect"] == "read"


def test_task_execute_and_receipt_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", list)
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    monkeypatch.setattr(
        "fixos.mcp_server.scan_unused_recent_project_artifacts",
        lambda min_age_days=7.0: [{"path": "/tmp/fake-proj/target", "size_bytes": 4096}],
    )
    monkeypatch.setattr(
        "fixos.mcp_server.scan_stale_app_state_partitions",
        lambda min_age_days=7.0: [],
    )

    receipts_dir = tmp_path / "receipts"
    first = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": True, "min_age_days": 7.0},
        registry_digest=catalog_digest(),
        request_id="req-test-001",
        receipts_dir=receipts_dir,
    )
    assert first["schema"] == RECEIPT_SCHEMA
    assert first["request_id"] == "req-test-001"
    assert first["state"] == "planned"
    assert first["planned_reclaimable_bytes"] == 4096
    assert first["replayed"] is False

    # Replay with same request_id returns stored receipt without re-running
    second = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": False},
        request_id="req-test-001",
        receipts_dir=receipts_dir,
    )
    assert second["replayed"] is True
    assert second["state"] == "planned"
    assert second["receipt_hash"] == first["receipt_hash"]

    status = task_status("req-test-001", receipts_dir=receipts_dir)
    assert status["found"] is True
    assert status["receipt_hash"] == first["receipt_hash"]


def test_task_execute_rejects_mismatched_digest():
    with pytest.raises(ValueError, match="CATALOG_DIGEST_MISMATCH"):
        task_execute("fixos://diagnostics/quick", {}, registry_digest="0" * 64)


@pytest.mark.parametrize("route", ["uri", "alias", "gateway", "jsonrpc"])
@pytest.mark.parametrize(
    "payload",
    [
        {"dry_run": "false"},
        {"dry_run": 0},
        {"dry_run": None},
        {"include_projects": "false"},
        {"include_projects": 1},
        {"min_age_days": float("nan")},
        {"min_age_days": float("inf")},
        {"min_age_days": float("-inf")},
        {"min_age_days": 0},
        {"min_age_days": -1},
        {"min_age_days": True},
        {"min_age_days": "7"},
        {"private-field": "submitted-secret"},
        {"request_id": []},
        {"request_id": "x" * 129},
    ],
)
def test_invalid_cleanup_arguments_never_reach_adapter(monkeypatch, route, payload):
    def forbidden_adapter(**kwargs):
        pytest.fail("Invalid arguments reached cleanup adapter")

    monkeypatch.setattr("fixos.mcp_server.run_fixos_auto_cleanup", forbidden_adapter)
    uri = "fixos://cleanup/auto"
    if route == "jsonrpc":
        response = handle_jsonrpc_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "fixos_auto_cleanup", "arguments": payload},
        })
        assert response["result"]["isError"] is True
        error = response["result"]["structuredContent"]["error"]
    else:
        with pytest.raises(ValueError, match="INVALID_ARGUMENTS") as caught:
            if route == "uri":
                task_execute(uri, payload)
            elif route == "alias":
                handle_mcp_tool_call("fixos_auto_cleanup", payload)
            else:
                handle_mcp_tool_call("task_execute", {"operation_id": uri, "payload": payload})
        error = str(caught.value)
    assert "private-field" not in error
    assert "submitted-secret" not in error


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("registry_search", {"query": 123}),
        ("registry_search", {"limit": True}),
        ("registry_search", {"limit": 0}),
        ("registry_search", {"limit": 51}),
        ("task_plan", {}),
        ("task_plan", {"task": ["cleanup"]}),
        ("task_execute", {}),
        ("task_execute", {"operation_id": ""}),
        ("task_execute", {"operation_id": "fixos://cleanup/auto", "payload": None}),
        ("task_execute", {"operation_id": "fixos://cleanup/auto", "payload": "{}"}),
        ("task_execute", {"operation_id": "fixos://cleanup/auto", "registry_digest": []}),
        ("fixos_task_status", {}),
        ("fixos_task_status", {"request_id": 123}),
        ("fixos_quick", {"unexpected": "submitted-secret"}),
        ("fixos_scan_disk", {"path": ""}),
        ("fixos_scan_disk", {"path": False}),
    ],
)
def test_invalid_tool_envelopes_do_not_dispatch(monkeypatch, name, arguments):
    def forbidden_dispatch(*args, **kwargs):
        pytest.fail("Invalid tool envelope reached dispatch")

    for handler in ("registry_search", "task_plan", "task_execute", "task_status"):
        monkeypatch.setattr(f"fixos.mcp_server.{handler}", forbidden_dispatch)
    response = handle_jsonrpc_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    assert response["result"]["isError"] is True
    assert "INVALID_ARGUMENTS" in response["result"]["structuredContent"]["error"]
    assert "submitted-secret" not in json.dumps(response)


@pytest.mark.parametrize("arguments", [None, [], "{}", False])
def test_jsonrpc_rejects_nonobject_arguments(monkeypatch, arguments):
    def forbidden_dispatch(*args, **kwargs):
        pytest.fail("Non-object arguments reached dispatch")

    monkeypatch.setattr("fixos.mcp_server.handle_mcp_tool_call", forbidden_dispatch)
    response = handle_jsonrpc_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "fixos_quick", "arguments": arguments},
    })
    assert response["result"]["isError"] is True


def test_valid_boolean_arguments_and_defaults_are_preserved(monkeypatch):
    monkeypatch.setattr("fixos.mcp_server.run_fixos_auto_cleanup", lambda **kwargs: kwargs)
    result = handle_mcp_tool_call("task_execute", {
        "operation_id": "fixos://cleanup/auto",
        "payload": {"dry_run": False, "include_projects": False, "min_age_days": 1},
    })
    assert result["dry_run"] is False
    assert result["include_projects"] is False
    assert result["min_age_days"] == 1
    assert task_execute("fixos://cleanup/auto")["dry_run"] is True


def test_unknown_operations_and_unsupported_constraints_fail_closed(monkeypatch):
    import fixos.mcp_server as server

    op = dict(server.OPERATIONS_CATALOG[0])
    op["input_schema"] = {**op["input_schema"], "minProperties": 1}
    monkeypatch.setattr(server, "OPERATIONS_CATALOG", (op,))
    monkeypatch.setattr(server, "run_fixos_quick", lambda: pytest.fail("Unexpected diagnostic"))
    with pytest.raises(ValueError, match="UNSUPPORTED_INPUT_SCHEMA"):
        task_execute(op["operation_id"])
    with pytest.raises(ValueError, match="^UNKNOWN_OPERATION$"):
        task_execute("submitted-secret")
    response = handle_jsonrpc_message({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "submitted-secret", "arguments": {}},
    })
    assert response["result"]["isError"] is True
    assert "submitted-secret" not in json.dumps(response)


@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize(
    "request_id",
    ["../escaped", "/absolute", r"..\escaped", "nested/id", "C:escaped", "bad\x00id", "..", ".hidden", "bad id", "x" * 129],
)
def test_cleanup_rejects_unsafe_request_ids_before_any_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request_id: str, dry_run: bool
):
    def unexpected_access(*args, **kwargs):
        pytest.fail("Invalid request ID reached receipt access or cleanup scanning")

    for name in ("_receipts_dir", "scan_user_cache_dirs", "scan_additional_safe_caches", "scan_build_and_package_caches"):
        monkeypatch.setattr(f"fixos.mcp_server.{name}", unexpected_access)

    with pytest.raises(ValueError, match="invalid_request_id"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": dry_run, "include_projects": False},
            request_id=request_id,
            receipts_dir=tmp_path / "receipts",
        )
    assert list(tmp_path.iterdir()) == []


def test_jsonrpc_reports_unsafe_receipt_id_without_creating_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", list)
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "fixos_auto_cleanup",
                "arguments": {"request_id": "../escaped", "include_projects": False},
            },
        },
        receipts_dir=tmp_path / "receipts",
    )
    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["error"] == "invalid_request_id"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("request_id", ["", "../escaped", r"nested\id", "C:escaped", "bad\x00id", "x" * 129])
def test_status_rejects_unsafe_ids_without_accessing_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request_id: str
):
    def unexpected_access(*args, **kwargs):
        pytest.fail("Invalid status request reached receipt directory access")

    monkeypatch.setattr("fixos.mcp_server._receipts_dir", unexpected_access)
    result = task_status(request_id, receipts_dir=tmp_path / "receipts")
    assert result["found"] is False
    assert result["error"] == "invalid_request_id"
    assert list(tmp_path.iterdir()) == []


def test_generated_receipt_id_remains_replayable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", list)
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    result = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": True, "include_projects": False},
        receipts_dir=tmp_path,
    )
    assert result["request_id"].startswith("fixos-mcp-")
    assert task_status(result["request_id"], receipts_dir=tmp_path)["receipt_hash"] == result["receipt_hash"]


def test_jsonrpc_protocol_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda: {"os": "Linux", "disk_free_bytes": 123456789},
    )

    init_resp = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init_resp is not None
    assert init_resp["result"]["serverInfo"]["name"] == "fixos-mcp"

    list_resp = handle_jsonrpc_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert list_resp is not None
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    assert {
        "registry_search",
        "task_plan",
        "task_execute",
        "fixos_task_status",
        "fixos_quick",
        "fixos_scan_disk",
        "fixos_scan_projects",
        "fixos_auto_cleanup",
    } <= tool_names

    call_resp = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "fixos_quick", "arguments": {}},
        },
        receipts_dir=tmp_path,
    )
    assert call_resp is not None
    assert call_resp["result"]["isError"] is False
    assert call_resp["result"]["structuredContent"]["operation_id"] == "fixos://diagnostics/quick"


def test_cli_mcp_subcommand():
    runner = CliRunner()
    cat_res = runner.invoke(cli, ["mcp", "--catalog"])
    assert cat_res.exit_code == 0
    cat_data = json.loads(cat_res.output)
    assert cat_data["schema"] == CATALOG_SCHEMA

    tools_res = runner.invoke(cli, ["mcp", "--tools"])
    assert tools_res.exit_code == 0
    tools_data = json.loads(tools_res.output)
    assert len(tools_data["tools"]) == len(mcp_tools_list())

    plan_res = runner.invoke(cli, ["mcp", "--plan", "zwolnij miejsce na dysku"])
    assert plan_res.exit_code == 0
    plan_data = json.loads(plan_res.output)
    assert plan_data["operation_id"] == "fixos://cleanup/auto"


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_cleanup_keeps_stdio_jsonrpc_parseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, cleanup_fails: bool
):
    monkeypatch.setattr(
        "fixos.mcp_server.scan_user_cache_dirs",
        lambda: [{"safe": True, "size_bytes": 4096}],
    )
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    cleanup_calls = []

    def cleanup(**kwargs):
        cleanup_calls.append(kwargs)
        print("Measuring cache")
        click.echo("Cleaning cache")
        if cleanup_fails:
            raise RuntimeError("cleanup failed")

    monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_user_cache", cleanup)
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "fixos_auto_cleanup",
                "arguments": {
                    "dry_run": False,
                    "include_projects": False,
                    "request_id": "stdio-cleanup",
                },
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    ]
    if not cleanup_fails:
        # A client retry after cleanup must replay its receipt without effects.
        requests.append({**requests[0], "id": 3})
    monkeypatch.setattr(
        "sys.stdin", io.StringIO("".join(json.dumps(req) + "\n" for req in requests))
    )

    assert serve_stdio(receipts_dir=tmp_path) == 0

    output = capsys.readouterr()
    responses = [json.loads(line) for line in output.out.splitlines()]
    assert [resp["id"] for resp in responses] == ([1, 2] if cleanup_fails else [1, 2, 3])
    assert responses[0]["result"]["isError"] is cleanup_fails
    assert responses[1] == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert "Measuring cache" in output.err
    assert "Cleaning cache" in output.err
    assert len(cleanup_calls) == 1
    if cleanup_fails:
        assert responses[0]["result"]["structuredContent"]["error"] == "cleanup failed"
    else:
        assert responses[0]["result"]["structuredContent"]["state"] == "succeeded"
        replay = responses[2]["result"]["structuredContent"]
        assert replay["replayed"] is True
        assert replay["receipt_hash"] == responses[0]["result"]["structuredContent"]["receipt_hash"]
        assert task_status("stdio-cleanup", receipts_dir=tmp_path)["found"] is True
