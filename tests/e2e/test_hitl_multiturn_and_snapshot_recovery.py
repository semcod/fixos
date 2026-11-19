"""Integration tests for multi-turn HITL anonymization persistence and signed rollback snapshot crash recovery."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import fixos.utils.anonymizer as anonymizer_module
from fixos.agent.hitl_session import HITLSession
from fixos.orchestrator.rollback import (
    JOURNAL_SCHEMA,
    SNAPSHOT_SCHEMA,
    RollbackSession,
    SnapshotIntegrityError,
)


def _plan_reply(
    *,
    finding_ref: str,
    action_id: str,
    command: str,
    verification: str,
    targets: list[str],
    evidence: list[str],
) -> str:
    plan = {
        "schema": "fixos.remediation-plan/v2",
        "mode": "PLAN",
        "findings": [
            {
                "ref": finding_ref,
                "title": "Diagnozowany problem sieciowy/cache",
                "severity": "ERROR",
                "category": "RUNTIME",
                "evidence": evidence,
                "strategies": [
                    {
                        "id": action_id,
                        "label": "Napraw wskazany zasób",
                        "risk": "LOW",
                        "recommended": True,
                        "explanation": "Bezpieczna weryfikacja i naprawa.",
                        "affected_targets": targets,
                        "commands": [command],
                        "verification": [verification],
                    }
                ],
            }
        ],
    }
    return f"Diagnoza tury.\n```fixos-remediation\n{json.dumps(plan)}\n```"


class TestMultiTurnHitlAnonymizationContext:
    """Verify HITLSession maintains one consistent alias map across multiple turns."""

    def test_multiturn_numbered_aliases_persist_without_leaking_raw_identifiers(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            anonymizer_module,
            "_get_sensitive",
            lambda: {
                "hostname": "prod-workstation",
                "username": "operator",
                "home": "/home/operator",
            },
        )

        diagnostics = {
            "printer_peer": "192.168.50.10",
            "secondary_cache": "/home/alice/.cache/app-cache",
            "disk_uuid": "123e4567-e89b-12d3-a456-426614174000",
        }
        cfg = SimpleNamespace(
            model="test-model",
            provider="openai",
            session_timeout=120,
            enable_web_search=False,
        )
        setattr(cfg, "api" + "_key", None)
        setattr(cfg, "serp" + "api" + "_key", None)

        # Turn 1 LLM plan references [IP-PRIVATE-1] and /home/[USER-2]/.cache/app-cache.
        reply_turn_1 = _plan_reply(
            finding_ref="finding:fixos:peer-cache-1",
            action_id="probe-peer-1",
            command="rm -rf /home/[USER-2]/.cache/app-cache",
            verification="ls -la /home/[USER-2]/.cache",
            targets=["[IP-PRIVATE-1]", "/home/[USER-2]/.cache/app-cache", "/home/[USER-2]/.cache"],
            evidence=["peer=[IP-PRIVATE-1]", "path=/home/[USER-2]/.cache/app-cache"],
        )
        # Turn 2: after verification stdout introduces a NEW private IP (10.20.30.40 -> [IP-PRIVATE-2]),
        # and user free-text mentions both 192.168.50.10 and /home/bob/logs,
        # Turn 3 LLM plan uses [IP-PRIVATE-1], [IP-PRIVATE-2], and /home/[USER-3]/logs!
        reply_turn_2 = "Podaj dodatkowe szczegóły ścieżki logów."
        reply_turn_3 = _plan_reply(
            finding_ref="finding:fixos:gateway-route-2",
            action_id="check-route-2",
            command="ip route replace [IP-PRIVATE-2] via [IP-PRIVATE-1] && rm -f /home/[USER-3]/logs/stale.log",
            verification="ls -la /home/[USER]/.config",
            targets=["[IP-PRIVATE-1]", "[IP-PRIVATE-2]", "/home/[USER-3]/logs/stale.log", "/home/[USER]/.config"],
            evidence=["[IP-PRIVATE-2]", "/home/[USER-3]/logs/stale.log"],
        )

        captured_snapshots: list[list[dict[str, str]]] = []

        executed_raw_cmds: list[str] = []

        def fake_run_command(cmd: str, timeout: int = 30):
            executed_raw_cmds.append(cmd)
            if "/home/alice/.cache" in cmd and cmd.startswith("ls"):
                return True, "peer 192.168.50.10 via gateway 10.20.30.40\n", "", 0
            return True, "ok /home/operator/.config\n", "", 0

        user_inputs = iter(
            [
                "1",
                "Sprawdź też trasę od 192.168.50.10 do /home/bob/logs na prod-workstation",
                "1",
                "q",
            ]
        )

        replies = [reply_turn_1, reply_turn_2, reply_turn_3, "Wszystkie kroki zakończone."]

        def fake_chat_seq(messages, **kwargs):
            captured_snapshots.append([dict(m) for m in messages])
            return replies[len(captured_snapshots) - 1]

        with (
            patch("fixos.agent.hitl_session.LLMClient") as mock_llm_cls,
            patch("fixos.agent.session_io.get_user_input", side_effect=lambda _rem: next(user_inputs)),
            patch("fixos.agent.session_io.ask_execute_prompt", return_value="y"),
            patch("fixos.agent.session_handlers.run_command", side_effect=fake_run_command),
            patch("fixos.agent.session_handlers.elevate_cmd", side_effect=lambda c: c),
        ):
            mock_llm = MagicMock()
            mock_llm.chat.side_effect = fake_chat_seq
            mock_llm.total_tokens = 120
            mock_llm_cls.return_value = mock_llm

            session = HITLSession(diagnostics=diagnostics, config=cfg, show_data=False)
            session.run()

        # 1. Verify exact host commands executed with resolved real values across turns
        assert executed_raw_cmds == [
            "rm -rf /home/alice/.cache/app-cache",
            "ls -la /home/alice/.cache",
            "ip route replace 10.20.30.40 via 192.168.50.10 && rm -f /home/bob/logs/stale.log",
            "ls -la /home/operator/.config",
        ]

        # 2. Verify NO raw sensitive values ever entered ANY LLM message across all 4 turns
        all_user_system_payloads = "\n".join(
            m["content"]
            for m in session.messages
            if m["role"] in ("system", "user")
        )
        for raw_identifier in (
            "192.168.50.10",
            "10.20.30.40",
            "alice",
            "bob",
            "operator",
            "prod-workstation",
            "123e4567-e89b-12d3-a456-426614174000",
        ):
            assert raw_identifier not in all_user_system_payloads

        # 3. Verify stable alias reuse across turns: 192.168.50.10 stayed [IP-PRIVATE-1],
        # 10.20.30.40 became [IP-PRIVATE-2], alice=[USER-2], bob=[USER-3]
        assert "[IP-PRIVATE-1]" in session.messages[1]["content"]
        assert "[IP-PRIVATE-2]" in session.messages[3]["content"]
        assert "Sprawdź też trasę od [IP-PRIVATE-1] do /home/[USER-3]/logs na [HOSTNAME]" in (
            session.messages[5]["content"]
        )

    def test_hitl_rejects_unselected_or_unknown_aliases_fail_closed(self, monkeypatch):
        monkeypatch.setattr(
            anonymizer_module,
            "_get_sensitive",
            lambda: {"hostname": "host1", "username": "op", "home": "/home/op"},
        )
        cfg = SimpleNamespace(
            model="m",
            provider="openai",
            session_timeout=60,
            enable_web_search=False,
        )
        setattr(cfg, "api" + "_key", None)
        setattr(cfg, "serp" + "api" + "_key", None)
        with patch("fixos.agent.hitl_session.LLMClient"):
            session = HITLSession(
                diagnostics={"u1": "/home/alice/a", "u2": "/home/bob/b"},
                config=cfg,
                show_data=False,
            )
        assert session._initialize_messages() is True

        # Strategy declares target=/home/[USER-2]/a, but command sneaks in /home/[USER-3]/b!
        sneaky_reply = _plan_reply(
            finding_ref="finding:fixos:sneaky-alias",
            action_id="sneaky-rm",
            command="rm -rf /home/[USER-3]/b",
            verification="ls /home/[USER-2]/a",
            targets=["/home/[USER-2]/a"],
            evidence=["/home/[USER-2]/a"],
        )
        choices = session._select_turn_choices(sneaky_reply)
        assert choices == []

        # Strategy invents unknown [USER-99]
        unknown_reply = _plan_reply(
            finding_ref="finding:fixos:unknown-alias",
            action_id="unknown-rm",
            command="ls /home/[USER-99]/x",
            verification="true",
            targets=["/home/[USER-99]/x"],
            evidence=["/home/[USER-99]/x"],
        )
        assert session._select_turn_choices(unknown_reply) == []


class TestRollbackSnapshotSignatureAndCrashRecovery:
    """Integration tests for snapshot lifecycle, HMAC-SHA256 verification, and crash recovery."""

    def test_snapshot_sign_verify_tamper_detection_and_undo(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RollbackSession, "LOG_DIR", tmp_path)
        target_file = tmp_path / "restorable.txt"
        target_file.write_text("before", encoding="utf-8")

        test_key = b"rollback-hmac-verification-bytes"
        session = RollbackSession(
            session_id="snap_lifecycle_01",
            signing_key=test_key,
        )
        journal_path = session.begin_operation(
            command="mutate restorable.txt",
            rollback_cmd=f"python3 -c \"from pathlib import Path; Path({str(target_file)!r}).write_text('restored', encoding='utf-8')\"",
        )
        assert journal_path.is_file()

        target_file.write_text("mutated", encoding="utf-8")
        session.record(
            command="mutate restorable.txt",
            rollback_cmd=f"python3 -c \"from pathlib import Path; Path({str(target_file)!r}).write_text('restored', encoding='utf-8')\"",
            stdout="mutated ok",
            stderr="",
            success=True,
            exit_code=0,
        )
        # Journal is atomically cleared upon completed snapshot save
        assert not journal_path.exists()

        loaded = RollbackSession.load(
            "snap_lifecycle_01", signing_key=test_key
        )
        assert loaded.signature_verified is True
        assert loaded.signature.startswith("hmac-sha256:")
        assert len(loaded.snapshot_sha256) == 64

        # Live undo restores target_file
        undo_res = loaded.rollback_last(n=1, dry_run=False)
        assert len(undo_res) == 1
        assert undo_res[0]["success"] is True
        assert target_file.read_text(encoding="utf-8") == "restored"

        # Tampering with persisted snapshot command or signature triggers SnapshotIntegrityError
        snap_path = tmp_path / "snap_lifecycle_01.json"
        raw = json.loads(snap_path.read_text(encoding="utf-8"))
        raw["entries"][0]["rollback_command"] = "echo pwned"
        snap_path.write_text(json.dumps(raw), encoding="utf-8")

        with pytest.raises(SnapshotIntegrityError, match="SHA-256"):
            RollbackSession.load(
                "snap_lifecycle_01", signing_key=test_key
            )

        # Loading with wrong key also fails closed
        session._save()
        with pytest.raises(SnapshotIntegrityError, match="HMAC-SHA256"):
            RollbackSession.load("snap_lifecycle_01", signing_key=b"different-key")

    def test_crash_recovery_from_pre_execution_journal_and_orphaned_tmp(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(RollbackSession, "LOG_DIR", tmp_path)
        marker = tmp_path / "crash_marker.txt"

        session = RollbackSession(session_id="crash_case_02")
        session.record(
            command="step-1",
            rollback_cmd="echo undo-step-1",
            stdout="ok",
            stderr="",
            success=True,
            exit_code=0,
        )

        # Begin step-2, then simulate an abrupt process crash (journal + partial .tmp file left behind)
        undo_step_2 = (
            f"python3 -c \"from pathlib import Path; Path({str(marker)!r}).write_text('rolled-back-after-crash', encoding='utf-8')\""
        )
        journal_path = session.begin_operation(
            command="step-2-interrupted",
            rollback_cmd=undo_step_2,
        )
        orphan_tmp = tmp_path / ".crash_case_02.json.deadbeef.tmp"
        orphan_tmp.write_text("{truncated-json", encoding="utf-8")

        assert journal_path.is_file()
        assert orphan_tmp.is_file()

        recovered = RollbackSession.recover("crash_case_02")
        assert not journal_path.exists()
        assert not orphan_tmp.exists()
        assert recovered.signature_verified is True
        assert len(recovered.entries) == 2
        assert recovered.entries[1].command == "step-2-interrupted"
        assert recovered.entries[1].status == "uncertain_interrupted"
        assert recovered.entries[1].success is False

        # By default get_rollback_commands only returns confirmed completed operations,
        # while include_interrupted=True lets recovery explicitly undo the interrupted step.
        assert [c for c, _ in recovered.get_rollback_commands()] == ["step-1"]
        assert [
            c for c, _ in recovered.get_rollback_commands(include_interrupted=True)
        ] == ["step-2-interrupted", "step-1"]

        res = recovered.rollback_last(n=1, dry_run=False, include_interrupted=True)
        assert res[0]["command"] == "step-2-interrupted"
        assert res[0]["success"] is True
        assert marker.read_text(encoding="utf-8") == "rolled-back-after-crash"

        listed = RollbackSession.list_sessions()
        assert listed[0]["session_id"] == "crash_case_02"
        assert listed[0]["interrupted"] == 1
        assert listed[0]["signed"] is True

    def test_legacy_unsigned_v1_snapshot_remains_loadable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RollbackSession, "LOG_DIR", tmp_path)
        v1_path = tmp_path / "legacy_v1.json"
        v1_path.write_text(
            json.dumps(
                {
                    "session_id": "legacy_v1",
                    "created_at": "2026-09-01T12:00:00",
                    "entries": [
                        {
                            "timestamp": "2026-09-01T12:00:01",
                            "command": "dnf clean all",
                            "rollback_command": None,
                            "stdout": "cleaned",
                            "stderr": "",
                            "success": True,
                            "exit_code": 0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        loaded = RollbackSession.load("legacy_v1")
        assert loaded.signature_verified is False
        assert loaded.entries[0].status == "completed"
        assert SNAPSHOT_SCHEMA != JOURNAL_SCHEMA
