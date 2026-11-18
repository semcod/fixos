"""Unit tests for input-bound MCP idempotency, pre-effect journals, and read-back receipts (#163)."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from fixos.mcp_receipts import (
    JOURNAL_SCHEMA,
    atomic_write_json,
    execute_with_durable_journal,
    read_durable_receipt,
    verify_receipt_integrity,
)
from fixos.mcp_server import catalog_digest, task_execute, task_status
from fixos.poa_grants import (
    cleanup_poa_input,
    cleanup_poa_target,
    issue_poa_grant,
    jcs_sha256,
    plan_cleanup_poa,
)


def _issue_cleanup_grant(grants_dir: Path, *, min_age_days: float = 7.0, include_projects: bool = False):
    digest = catalog_digest()
    plan = plan_cleanup_poa(
        registry_digest=digest,
        min_age_days=min_age_days,
        include_projects=include_projects,
    )
    grant = issue_poa_grant(plan, store_dir=grants_dir)
    return digest, plan, grant


def test_single_flight_concurrent_calls_execute_effect_once(tmp_path: Path):
    base_dir = tmp_path / "receipts"
    call_count = 0
    count_lock = threading.Lock()

    def slow_runner(_started_at: str):
        nonlocal call_count
        with count_lock:
            call_count += 1
        time.sleep(0.08)
        return {"state": "succeeded", "actions": ["demo:1"], "readback": {"verified": True}}, None

    def worker():
        return execute_with_durable_journal(
            base_dir=base_dir,
            request_id="concurrent-req-1",
            correlation_id="corr-concurrent",
            operation_id="fixos://cleanup/auto",
            effect="mutate",
            dry_run=False,
            registry_digest="a" * 64,
            input_digest="b" * 64,
            target={"host": "local", "root": "/"},
            runner=slow_runner,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: worker(), range(4)))

    assert call_count == 1
    assert sum(1 for r in results if not r["replayed"]) == 1
    assert sum(1 for r in results if r["replayed"]) == 3
    hashes = {r["receipt_hash"] for r in results}
    assert len(hashes) == 1
    assert results[0]["receipt_urn"].startswith("urn:uuid:")
    assert results[0]["correlation_id"] == "corr-concurrent"
    assert verify_receipt_integrity(results[0]) is True


def test_interrupted_pre_effect_journal_recovers_as_uncertain_without_reexecuting(tmp_path: Path):
    base_dir = tmp_path / "receipts"
    norm_in = cleanup_poa_input(dry_run=False, min_age_days=7.0, include_projects=False)
    input_digest = jcs_sha256(norm_in)
    digest = catalog_digest()
    journal_path = base_dir / "crashed-001.journal.json"
    atomic_write_json(
        journal_path,
        {
            "schema": JOURNAL_SCHEMA,
            "request_id": "crashed-001",
            "correlation_id": "corr-crash",
            "operation_id": "fixos://cleanup/auto",
            "effect": "mutate",
            "dry_run": False,
            "state": "in_progress",
            "started_at": "2026-11-18T16:00:00Z",
            "registry_digest": digest,
            "input_digest": input_digest,
            "target": cleanup_poa_target(include_projects=False, min_age_days=7.0),
        },
    )

    effect_ran = False

    def forbidden_runner(_started: str):
        nonlocal effect_ran
        effect_ran = True
        return {"state": "succeeded"}, None

    recovered = execute_with_durable_journal(
        base_dir=base_dir,
        request_id="crashed-001",
        correlation_id="corr-crash",
        operation_id="fixos://cleanup/auto",
        effect="mutate",
        dry_run=False,
        registry_digest=digest,
        input_digest=input_digest,
        target=cleanup_poa_target(include_projects=False, min_age_days=7.0),
        runner=forbidden_runner,
    )
    assert effect_ran is False
    assert recovered["state"] == "uncertain"
    assert recovered["interrupted"] is True
    assert recovered["replayed"] is True
    assert not journal_path.exists()
    assert (base_dir / "crashed-001.json").is_file()

    # Conflicting retry against recovered uncertain receipt also fails closed
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        execute_with_durable_journal(
            base_dir=base_dir,
            request_id="crashed-001",
            correlation_id="corr-crash",
            operation_id="fixos://cleanup/auto",
            effect="mutate",
            dry_run=False,
            registry_digest=digest,
            input_digest="f" * 64,
            target=cleanup_poa_target(include_projects=False, min_age_days=7.0),
            runner=forbidden_runner,
        )


def test_corrupted_receipt_and_write_failure_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    base_dir = tmp_path / "receipts"
    base_dir.mkdir(parents=True)
    bad_file = base_dir / "corrupt-01.json"
    bad_file.write_text("{not-valid-json", encoding="utf-8")

    status = read_durable_receipt("corrupt-01", base_dir=base_dir)
    assert status["found"] is True
    assert status["valid"] is False
    assert status["state"] == "uncertain"
    assert status["error"] == "CORRUPTED_RECEIPT"

    with pytest.raises(ValueError, match="CORRUPTED_RECEIPT"):
        execute_with_durable_journal(
            base_dir=base_dir,
            request_id="corrupt-01",
            correlation_id="",
            operation_id="fixos://cleanup/auto",
            effect="read",
            dry_run=True,
            registry_digest="a" * 64,
            input_digest="b" * 64,
            target={"host": "local"},
            runner=lambda _: ({"state": "planned"}, None),
        )

    # Tampered hash detection
    tampered = base_dir / "tampered-01.json"
    tampered.write_text(
        json.dumps({"schema": "wellmanifest.mcp/task-receipt/v1", "request_id": "tampered-01", "receipt_hash": "0" * 64}),
        encoding="utf-8",
    )
    t_status = task_status("tampered-01", receipts_dir=base_dir)
    assert t_status["valid"] is False
    assert t_status["error"] == "CORRUPTED_RECEIPT"

    # Simulated write failure during final receipt os.replace leaves journal intact -> uncertain recovery
    real_replace = __import__("os").replace
    calls = 0

    def flaky_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk full on receipt commit")
        real_replace(src, dst)

    monkeypatch.setattr("fixos.mcp_receipts.os.replace", flaky_replace)
    with pytest.raises(RuntimeError, match="RECEIPT_WRITE_FAILED"):
        execute_with_durable_journal(
            base_dir=base_dir,
            request_id="write-fail-01",
            correlation_id="corr-wf",
            operation_id="fixos://cleanup/auto",
            effect="mutate",
            dry_run=False,
            registry_digest="c" * 64,
            input_digest="d" * 64,
            target={"host": "local"},
            runner=lambda _: ({"state": "succeeded"}, None),
        )
    assert (base_dir / "write-fail-01.journal.json").is_file()

    monkeypatch.setattr("fixos.mcp_receipts.os.replace", real_replace)
    after_crash = task_status("write-fail-01", receipts_dir=base_dir)
    assert after_crash["state"] == "uncertain"
    assert after_crash["interrupted"] is True


def test_post_cleanup_readback_reports_partial_failed_and_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    receipts_dir = tmp_path / "receipts"
    grants_dir = tmp_path / "grants"

    # 1. Partial: 2 items planned, helper silently skips 1 item -> read-back sees 1 remaining -> state == "partial"
    items_state = [
        {"safe": True, "path": str(tmp_path / "c1"), "size_bytes": 1000},
        {"safe": True, "path": str(tmp_path / "c2"), "size_bytes": 2000},
    ]
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", lambda: list(items_state))
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    monkeypatch.setattr(
        "fixos.cli._cleanup_space._cleanup_user_cache",
        lambda **kwargs: items_state.pop(0),
    )

    digest, plan1, grant1 = _issue_cleanup_grant(grants_dir)
    res_partial = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": False, "include_projects": False},
        registry_digest=digest,
        request_id="req-partial",
        plan_hash=plan1["plan_hash"],
        grant_id=grant1["grantId"],
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert res_partial["state"] == "partial"
    assert res_partial["readback"] == {
        "verified": True,
        "planned_targets": 2,
        "remaining_targets": 1,
        "removed_targets": 1,
    }

    # 2. Failed: 1 item planned, helper silently removes 0 items -> state == "failed"
    monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_user_cache", lambda **kwargs: None)
    digest, plan2, grant2 = _issue_cleanup_grant(grants_dir)
    res_failed = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": False, "include_projects": False},
        registry_digest=digest,
        request_id="req-silent-fail",
        plan_hash=plan2["plan_hash"],
        grant_id=grant2["grantId"],
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert res_failed["state"] == "failed"
    assert res_failed["readback"]["removed_targets"] == 0

    # 3. Uncertain: post-cleanup read-back throws an error -> state == "uncertain"
    scan_calls = 0

    def scan_then_fail():
        nonlocal scan_calls
        scan_calls += 1
        if scan_calls == 1:
            return [{"safe": True, "path": str(tmp_path / "c2"), "size_bytes": 2000}]
        raise OSError("filesystem read-back unavailable")

    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", scan_then_fail)
    digest, plan3, grant3 = _issue_cleanup_grant(grants_dir)
    res_uncertain = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": False, "include_projects": False},
        registry_digest=digest,
        request_id="req-rb-uncertain",
        plan_hash=plan3["plan_hash"],
        grant_id=grant3["grantId"],
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert res_uncertain["state"] == "uncertain"
    assert res_uncertain["readback"]["verified"] is False
