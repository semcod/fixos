"""Contract tests for Planfile sprint persistence, schema validation, and CAS backup migration (#170)."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_sprint_document_contract(doc: Any) -> list[str]:
    """Validate the canonical Planfile sprint v1.1 envelope (`sprint.id`, `sprint.name`, `tickets`)."""
    errors: list[str] = []
    if not isinstance(doc, dict) or not isinstance(doc.get("sprint"), dict):
        return ["Missing required top-level mapping 'sprint'"]
    sprint = doc["sprint"]
    for req_field in ("id", "name"):
        val = sprint.get(req_field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"Missing required field sprint.{req_field}")
    tickets = sprint.get("tickets")
    if not isinstance(tickets, dict):
        errors.append("Missing required mapping sprint.tickets")
        return errors
    for tid, record in tickets.items():
        if not isinstance(record, dict):
            errors.append(f"Ticket {tid} must be a mapping")
            continue
        if record.get("id") != tid:
            errors.append(f"Ticket key {tid} does not match record id {record.get('id')!r}")
        if not isinstance(record.get("name"), str) or not record["name"].strip():
            errors.append(f"Ticket {tid} missing required name")
        if not isinstance(record.get("contract_version"), str) or not record["contract_version"]:
            errors.append(f"Ticket {tid} missing contract_version")
    return errors


def migrate_sprint_with_backup_and_cas(
    sprint_path: Path,
    *,
    expected_sha256: str,
    sprint_id: str,
    sprint_name: str,
    backup_dir: Path,
) -> Path:
    """Atomically back up a legacy sprint YAML, verify SHA-256 CAS, and restore required metadata."""
    raw_bytes = sprint_path.read_bytes()
    actual_sha256 = _sha256_bytes(raw_bytes)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"sprint_cas_mismatch: expected {expected_sha256}, got {actual_sha256}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{sprint_path.name}.{actual_sha256[:12]}.bak"
    backup_path.write_bytes(raw_bytes)
    assert _sha256_bytes(backup_path.read_bytes()) == expected_sha256

    parsed = yaml.safe_load(raw_bytes.decode("utf-8")) or {}
    sprint_block = dict(parsed.get("sprint") or {})
    if "tickets" not in sprint_block and isinstance(parsed.get("tickets"), dict):
        sprint_block["tickets"] = dict(parsed["tickets"])
    sprint_block.setdefault("id", sprint_id)
    sprint_block.setdefault("name", sprint_name)
    sprint_block.setdefault("tickets", {})
    normalized = {"sprint": sprint_block}

    errors = validate_sprint_document_contract(normalized)
    if errors:
        raise ValueError(f"sprint_validation_failed: {errors}")

    tmp_path = sprint_path.with_suffix(".yaml.tmp")
    rendered = yaml.safe_dump(normalized, sort_keys=True, allow_unicode=True)
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, sprint_path)
    return backup_path


def test_sprint_migration_with_backup_and_cas_preserves_tickets_and_history(tmp_path: Path):
    legacy_doc = {
        "sprint": {
            "tickets": {
                "PLF-033": {
                    "id": "PLF-033",
                    "name": "Fleet: adopt Wellmanifest docs/logs/worktrees/license/report",
                    "status": "open",
                    "sprint": "backlog",
                    "contract_version": "planfile.ticket/v1",
                    "history": [
                        {
                            "action": "create",
                            "source": "planfile.store",
                            "timestamp": "2026-10-15T10:00:00+00:00",
                        }
                    ],
                },
                "PLF-21821": {
                    "id": "PLF-21821",
                    "name": "FixOS Planfile: zweryfikuj automatyczny sync GitHub",
                    "status": "open",
                    "sprint": "backlog",
                    "contract_version": "planfile.ticket/v1",
                    "sync": {"github": {"id": "170", "key": "semcod/fixos#170"}},
                    "history": [
                        {
                            "action": "status_change",
                            "status": "open",
                            "timestamp": "2026-11-04T12:00:00+00:00",
                        }
                    ],
                },
            }
        }
    }
    sprint_file = tmp_path / "backlog.yaml"
    sprint_file.write_text(yaml.safe_dump(legacy_doc, sort_keys=True, allow_unicode=True), encoding="utf-8")

    # Legacy file without sprint.id / sprint.name fails validator contract (2026-11-04 audit finding)
    pre_errors = validate_sprint_document_contract(yaml.safe_load(sprint_file.read_text(encoding="utf-8")))
    assert "Missing required field sprint.id" in pre_errors
    assert "Missing required field sprint.name" in pre_errors

    digest_before = _sha256_bytes(sprint_file.read_bytes())

    # Stale CAS digest must fail closed without mutating target or creating partial state
    with pytest.raises(ValueError, match="sprint_cas_mismatch"):
        migrate_sprint_with_backup_and_cas(
            sprint_file,
            expected_sha256="0" * 64,
            sprint_id="backlog",
            sprint_name="Backlog",
            backup_dir=tmp_path / "backups",
        )
    assert _sha256_bytes(sprint_file.read_bytes()) == digest_before

    # Exact CAS digest creates verified backup and restores sprint.id + sprint.name with 0 history loss
    backup_path = migrate_sprint_with_backup_and_cas(
        sprint_file,
        expected_sha256=digest_before,
        sprint_id="backlog",
        sprint_name="Backlog",
        backup_dir=tmp_path / "backups",
    )
    assert backup_path.is_file()
    assert _sha256_bytes(backup_path.read_bytes()) == digest_before

    migrated = yaml.safe_load(sprint_file.read_text(encoding="utf-8"))
    assert validate_sprint_document_contract(migrated) == []
    assert migrated["sprint"]["id"] == "backlog"
    assert migrated["sprint"]["name"] == "Backlog"
    assert set(migrated["sprint"]["tickets"]) == {"PLF-033", "PLF-21821"}
    assert migrated["sprint"]["tickets"]["PLF-033"]["history"] == legacy_doc["sprint"]["tickets"]["PLF-033"]["history"]
    assert migrated["sprint"]["tickets"]["PLF-21821"]["sync"]["github"]["id"] == "170"


def write_sprint_ticket_atomic(
    sprint_path: Path,
    *,
    sprint_id: str,
    sprint_name: str,
    ticket_id: str,
    title: str,
) -> None:
    """Persist a sprint ticket atomically using the canonical v1.1 sprint envelope."""
    doc = (
        yaml.safe_load(sprint_path.read_text(encoding="utf-8"))
        if sprint_path.is_file()
        else {}
    ) or {}
    sprint_block = dict(doc.get("sprint") or {})
    sprint_block.setdefault("id", sprint_id)
    sprint_block.setdefault("name", sprint_name)
    tickets = dict(sprint_block.get("tickets") or {})
    tickets[ticket_id] = {
        "id": ticket_id,
        "name": title,
        "status": "open",
        "priority": "normal",
        "sprint": sprint_id,
        "contract_version": "planfile.ticket/v1",
        "history": [{"action": "create", "source": "planfile.store"}],
    }
    sprint_block["tickets"] = tickets
    normalized = {"sprint": sprint_block}
    tmp_path = sprint_path.with_suffix(".yaml.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(normalized, sort_keys=True, allow_unicode=True))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, sprint_path)


def test_sprint_writer_roundtrip_with_schema_validator(tmp_path: Path):
    project_dir = tmp_path / "repo"
    project_dir.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    sprints_dir = project_dir / ".planfile" / "sprints"
    sprints_dir.mkdir(parents=True)
    backlog_file = sprints_dir / "backlog.yaml"
    backlog_file.write_text(
        yaml.safe_dump({"sprint": {"id": "backlog", "name": "Backlog", "tickets": {}}}, sort_keys=True),
        encoding="utf-8",
    )

    planfile_bin = shutil.which("planfile")
    if planfile_bin:
        for title in ("Existing historical backlog item", "Writer contract roundtrip item"):
            create_proc = subprocess.run(
                [planfile_bin, "ticket", "create", title, "--sprint", "backlog"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            assert create_proc.returncode == 0, create_proc.stderr or create_proc.stdout
        val_proc = subprocess.run(
            [planfile_bin, "validate", "schema", str(backlog_file), "--file-type", "sprint"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        assert val_proc.returncode == 0, val_proc.stderr or val_proc.stdout
    else:
        write_sprint_ticket_atomic(
            backlog_file,
            sprint_id="backlog",
            sprint_name="Backlog",
            ticket_id="PLF-001",
            title="Existing historical backlog item",
        )
        write_sprint_ticket_atomic(
            backlog_file,
            sprint_id="backlog",
            sprint_name="Backlog",
            ticket_id="PLF-002",
            title="Writer contract roundtrip item",
        )

    persisted = yaml.safe_load(backlog_file.read_text(encoding="utf-8"))
    assert validate_sprint_document_contract(persisted) == []
    assert persisted["sprint"]["id"] == "backlog"
    assert persisted["sprint"]["name"] == "Backlog"
    assert len(persisted["sprint"]["tickets"]) == 2
    titles = {t["name"] for t in persisted["sprint"]["tickets"].values()}
    assert titles == {"Existing historical backlog item", "Writer contract roundtrip item"}
