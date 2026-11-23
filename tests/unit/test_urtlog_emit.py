"""Unit tests for fail-open uritime.urtlog.record/v2 emission in fixOS."""

from __future__ import annotations

import json

from fixos.diagnostics import project_scanner as ps
from fixos.diagnostics.urtlog_emit import (
    FIXOS_ACTOR,
    URTLOG_RECORD_SCHEMA,
    emit_cleanup_summary,
    emit_cleanup_veto,
    emit_urtlog_record,
)


def test_emit_urtlog_record_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("FIXOS_URTLOG_STATE_DIR", raising=False)
    monkeypatch.delenv("URTLOG_STATE_DIR", raising=False)
    assert emit_urtlog_record(action="fixos.test", uri="proc://semcod/fixos/test/v1") is False


def test_emit_cleanup_summary_writes_valid_v2_record(tmp_path, monkeypatch):
    monkeypatch.setenv("URTLOG_STATE_DIR", str(tmp_path))
    ok = emit_cleanup_summary(
        mode="auto",
        reclaimed_bytes=1024 * 1024,
        steps=["user-cache", "docker-build-cache"],
        dry_run=False,
    )
    assert ok is True
    events_file = tmp_path / "events.jsonl"
    assert events_file.is_file()
    records = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    rec = records[0]
    assert rec["schema"] == URTLOG_RECORD_SCHEMA
    assert rec["actor"] == FIXOS_ACTOR
    assert rec["action"] == "fixos.cleanup_summary"
    assert rec["status"] == "succeeded"
    assert rec["details"]["reclaimed_bytes"] == 1024 * 1024
    assert rec["details"]["steps"] == ["user-cache", "docker-build-cache"]


def test_emit_cleanup_veto_fail_open_on_unwritable_path(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("file", encoding="utf-8")
    ok = emit_cleanup_veto(
        target="/tmp/demo",
        verdict="HOLD_PROTECTED",
        veto_codes=("VETO_ACTIVE_LEASE",),
        reasons=("Active lease",),
        state_dir=blocker,
    )
    assert ok is False


def test_project_scanner_emits_urtlog_on_hard_veto(tmp_path, monkeypatch):
    urtlog_dir = tmp_path / "urtlog"
    monkeypatch.setenv("FIXOS_URTLOG_STATE_DIR", str(urtlog_dir))

    proj = tmp_path / "leased_repo"
    (proj / ".git").mkdir(parents=True)
    lease_dir = proj / ".subactor" / "leases"
    lease_dir.mkdir(parents=True)
    (lease_dir / "ticket-001--demo.json").write_text(
        json.dumps({"ticketId": "ticket-001", "phase": "claimed", "ownerActor": "agent:codex"}),
        encoding="utf-8",
    )

    report = ps.evaluate_cleanup_vetos(proj)
    assert report.verdict == ps.VERDICT_HOLD_PROTECTED
    events_file = urtlog_dir / "events.jsonl"
    assert events_file.is_file()
    records = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["schema"] == URTLOG_RECORD_SCHEMA
    assert records[0]["action"] == "fixos.cleanup_veto"
    assert records[0]["status"] == "blocked"
    assert ps.VETO_ACTIVE_LEASE in records[0]["details"]["veto_codes"]
