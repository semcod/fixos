"""Unit tests for MCP URN resources (`resources/list`, `templates/list`, `read`) (#165)."""

from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fixos.mcp_resources import (
    CATALOG_RESOURCE_URN,
    FORBIDDEN_INTERNAL_URN,
    QUICK_SNAPSHOT_RESOURCE_URN,
    mcp_resources_list,
    mcp_resources_read,
)
from fixos.mcp_server import (
    catalog_digest,
    handle_jsonrpc_message,
    serve_stdio,
    task_execute,
)
from fixos.poa_grants import issue_poa_grant, plan_cleanup_poa


def test_initialize_advertises_resources_and_templates_list(tmp_path: Path):
    init = handle_jsonrpc_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        receipts_dir=tmp_path / "receipts",
        grants_dir=tmp_path / "grants",
    )
    assert init is not None
    caps = init["result"]["capabilities"]
    assert "resources" in caps
    assert caps["resources"] == {"subscribe": False, "listChanged": False}

    tmpl = handle_jsonrpc_message(
        {"jsonrpc": "2.0", "id": 2, "method": "resources/templates/list", "params": {}},
        receipts_dir=tmp_path / "receipts",
        grants_dir=tmp_path / "grants",
    )
    assert tmpl is not None
    templates = tmpl["result"]["resourceTemplates"]
    assert len(templates) == 1
    assert templates[0]["uriTemplate"] == "urn:uuid:{uuid}"


def test_resources_list_pagination_and_read_catalog_snapshot_plan_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    receipts_dir = tmp_path / "receipts"
    grants_dir = tmp_path / "grants"
    cleanup_invocations = 0

    def forbidden_cleanup(**kwargs):
        nonlocal cleanup_invocations
        cleanup_invocations += 1

    monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_user_cache", forbidden_cleanup)
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", list)
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda: {"os": "Linux", "cpu_percent": 12.5},
    )

    digest = catalog_digest()
    plan = plan_cleanup_poa(registry_digest=digest, include_projects=False)
    _grant = issue_poa_grant(plan, store_dir=grants_dir)
    receipt = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": True, "include_projects": False},
        registry_digest=digest,
        request_id="res-receipt-1",
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )

    page1 = mcp_resources_list(
        page_size=2,
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert len(page1["resources"]) == 2
    assert "nextCursor" in page1
    page2 = mcp_resources_list(
        cursor=page1["nextCursor"],
        page_size=2,
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert len(page2["resources"]) == 2
    assert "nextCursor" not in page2

    all_urns = {r["uri"] for r in page1["resources"] + page2["resources"]}
    assert {
        CATALOG_RESOURCE_URN,
        QUICK_SNAPSHOT_RESOURCE_URN,
        plan["plan_urn"],
        receipt["receipt_urn"],
    } <= all_urns
    assert all(u.startswith("urn:uuid:") for u in all_urns)

    for idx, urn in enumerate(
        (CATALOG_RESOURCE_URN, QUICK_SNAPSHOT_RESOURCE_URN, plan["plan_urn"], receipt["receipt_urn"]),
        start=10,
    ):
        resp = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": idx, "method": "resources/read", "params": {"uri": urn}},
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
        assert resp is not None
        assert "error" not in resp
        contents = resp["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == urn
        assert len(contents[0]["_meta"]["sha256"]) == 64
        parsed = json.loads(contents[0]["text"])
        assert isinstance(parsed, dict)

    assert cleanup_invocations == 0


def test_resources_reject_action_uri_unknown_forbidden_and_expired_over_clean_stdio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    receipts_dir = tmp_path / "receipts"
    grants_dir = tmp_path / "grants"
    digest = catalog_digest()

    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    expired_plan = plan_cleanup_poa(
        registry_digest=digest,
        include_projects=False,
        now=old_time,
    )
    grants_dir.mkdir(parents=True, exist_ok=True)
    (grants_dir / f"plan-{expired_plan['plan_hash']}.json").write_text(
        json.dumps(expired_plan),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="RESOURCE_RETENTION_EXPIRED"):
        mcp_resources_read(
            expired_plan["plan_urn"],
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
            quick_snapshot_loader=lambda: {"os": "Linux"},
            retention_days=30,
        )

    def noisy_snapshot() -> dict[str, str]:
        print("noisy snapshot progress")
        return {"os": "Linux"}

    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        noisy_snapshot,
    )

    unknown_urn = "urn:uuid:00000000-0000-4000-8000-000000000099"
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {"cursor": ""}},
        {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": QUICK_SNAPSHOT_RESOURCE_URN}},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": unknown_urn}},
        {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": FORBIDDEN_INTERNAL_URN}},
        {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "fixos://cleanup/auto"}},
        {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {"cursor": "not-a-number"}},
    ]
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("".join(json.dumps(r) + "\n" for r in requests)),
    )
    assert serve_stdio(receipts_dir=receipts_dir, grants_dir=grants_dir) == 0

    captured = capsys.readouterr()
    assert "noisy snapshot progress" in captured.err
    frames = [json.loads(line) for line in captured.out.splitlines()]
    assert [f["id"] for f in frames] == [1, 2, 3, 4, 5, 6]
    assert "result" in frames[0]
    assert "result" in frames[1]
    assert "error" in frames[2] and "UNKNOWN_RESOURCE_URN" in frames[2]["error"]["message"]
    assert "error" in frames[3] and "FORBIDDEN_RESOURCE_SCOPE" in frames[3]["error"]["message"]
    assert "error" in frames[4] and "ACTION_URI_NOT_READABLE_AS_RESOURCE" in frames[4]["error"]["message"]
    assert "error" in frames[5] and "INVALID_CURSOR" in frames[5]["error"]["message"]
