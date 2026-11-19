"""
Rollback and signed snapshot recovery system for fixOS.

Each fix session persists an atomically written, HMAC-SHA256 signed snapshot in
``~/.fixos/rollback/<session_id>.json`` (``fixos.rollback-snapshot/v2``) paired
with a pre-execution crash journal (``<session_id>.journal.json``) so interrupted
operations can be deterministically recovered and audited after a crash.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SNAPSHOT_SCHEMA = "fixos.rollback-snapshot/v2"
JOURNAL_SCHEMA = "fixos.rollback-journal/v1"
SIGNING_KEY_ENV = "FIXOS_SNAPSHOT_SIGNING_KEY"
_SESSION_ID_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


class SnapshotIntegrityError(ValueError):
    """Raised when a persisted rollback snapshot fails digest or HMAC verification."""


def _validate_session_id(session_id: str) -> str:
    clean = (session_id or "").strip()
    if not clean or len(clean) > 128 or any(ch not in _SESSION_ID_CHARS for ch in clean):
        raise ValueError(f"Invalid rollback session_id: {session_id!r}")
    return clean


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _atomic_write_json(target: Path, payload: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            with contextlib.suppress(OSError):
                os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except OSError:
        with contextlib.suppress(OSError):
            if tmp_path.exists():
                tmp_path.unlink()
        raise


def _resolve_signing_key(
    log_dir: Path,
    explicit_key: bytes | str | None = None,
) -> bytes:
    if explicit_key is not None:
        return (
            explicit_key
            if isinstance(explicit_key, bytes)
            else explicit_key.encode("utf-8")
        )
    env_key = os.environ.get(SIGNING_KEY_ENV)
    if env_key:
        return env_key.encode("utf-8")

    log_dir.mkdir(parents=True, exist_ok=True)
    key_path = log_dir / ".signing.key"
    if key_path.is_file():
        raw = key_path.read_text(encoding="utf-8").strip()
        if raw:
            return raw.encode("utf-8")

    generated = secrets.token_hex(32)
    tmp_key = log_dir / f".signing.key.{uuid.uuid4().hex}.tmp"
    try:
        fd = os.open(str(tmp_key), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(generated + "\n")
            handle.flush()
            with contextlib.suppress(OSError):
                os.fsync(handle.fileno())
        os.replace(tmp_key, key_path)
    except OSError:
        with contextlib.suppress(OSError):
            if tmp_key.exists():
                tmp_key.unlink()
    return generated.encode("utf-8")


def _compute_snapshot_digests(
    body: dict[str, Any],
    signing_key: bytes,
) -> tuple[str, str]:
    canonical = _canonical_bytes(body)
    sha256_hex = hashlib.sha256(canonical).hexdigest()
    sig_hex = hmac.new(signing_key, canonical, hashlib.sha256).hexdigest()
    return sha256_hex, f"hmac-sha256:{sig_hex}"


@dataclass
class RollbackEntry:
    """Single recorded operation with its rollback command and lifecycle status."""

    timestamp: str
    command: str
    rollback_command: str | None
    stdout: str
    stderr: str
    success: bool
    exit_code: int
    status: str = "completed"


@dataclass
class RollbackSession:
    """A signed session of recorded operations that supports crash recovery and undo."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    entries: list[RollbackEntry] = field(default_factory=list)
    signing_key: bytes | str | None = field(default=None, repr=False, compare=False)
    snapshot_sha256: str = field(default="", init=False)
    signature: str = field(default="", init=False)
    signature_verified: bool = field(default=False, init=False)

    LOG_DIR = Path.home() / ".fixos" / "rollback"

    def _snapshot_path(self) -> Path:
        return Path(self.LOG_DIR) / f"{_validate_session_id(self.session_id)}.json"

    def _journal_path(self) -> Path:
        return (
            Path(self.LOG_DIR)
            / f"{_validate_session_id(self.session_id)}.journal.json"
        )

    def begin_operation(
        self,
        command: str,
        rollback_cmd: str | None = None,
    ) -> Path:
        """Persist an atomic pre-execution crash journal before mutating host state."""
        journal_path = self._journal_path()
        log_dir = Path(self.LOG_DIR)
        key = _resolve_signing_key(log_dir, self.signing_key)
        body = {
            "schema": JOURNAL_SCHEMA,
            "session_id": _validate_session_id(self.session_id),
            "created_at": self.created_at,
            "started_at": datetime.now().isoformat(),
            "command": command,
            "rollback_command": rollback_cmd,
            "prior_entry_count": len(self.entries),
        }
        digest, sig = _compute_snapshot_digests(body, key)
        _atomic_write_json(
            journal_path,
            {
                **body,
                "journal_sha256": digest,
                "signature": sig,
            },
        )
        return journal_path

    def record(
        self,
        command: str,
        rollback_cmd: str | None,
        stdout: str,
        stderr: str,
        success: bool,
        exit_code: int,
        *,
        status: str = "completed",
    ) -> None:
        """Record a completed operation, atomically sign snapshot, and clear journal."""
        self.entries.append(
            RollbackEntry(
                timestamp=datetime.now().isoformat(),
                command=command,
                rollback_command=rollback_cmd,
                stdout=stdout[:2000],
                stderr=stderr[:1000],
                success=success,
                exit_code=exit_code,
                status=status,
            )
        )
        self._save()
        journal_path = self._journal_path()
        with contextlib.suppress(OSError):
            if journal_path.exists():
                journal_path.unlink()

    def get_rollback_commands(
        self,
        *,
        include_interrupted: bool = False,
    ) -> list[tuple[str, str]]:
        """Return ``(command, rollback_command)`` pairs in reverse chronological order."""
        eligible_statuses = (
            {"completed", "uncertain_interrupted"}
            if include_interrupted
            else {"completed"}
        )
        return [
            (e.command, e.rollback_command)
            for e in reversed(self.entries)
            if e.rollback_command
            and e.status in eligible_statuses
            and (e.success or (include_interrupted and e.status == "uncertain_interrupted"))
        ]

    @staticmethod
    def _run_rollback_cmd(rollback_cmd: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            rollback_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def rollback_last(
        self,
        n: int = 1,
        dry_run: bool = False,
        *,
        include_interrupted: bool = False,
    ) -> list[dict[str, Any]]:
        """Undo the most recent ``n`` rollbackable operations."""
        commands = self.get_rollback_commands(
            include_interrupted=include_interrupted
        )[:n]
        results: list[dict[str, Any]] = []

        for orig_cmd, rollback_cmd in commands:
            if dry_run:
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": None,
                        "output": "[DRY-RUN]",
                    }
                )
                continue

            try:
                proc = self._run_rollback_cmd(rollback_cmd)
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": proc.returncode == 0,
                        "output": proc.stdout.strip() or proc.stderr.strip(),
                    }
                )
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": False,
                        "output": str(exc),
                    }
                )

        return results

    def _snapshot_body(self) -> dict[str, Any]:
        return {
            "schema": SNAPSHOT_SCHEMA,
            "session_id": _validate_session_id(self.session_id),
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }

    def _save(self) -> None:
        """Atomically persist and HMAC-sign the session snapshot."""
        log_dir = Path(self.LOG_DIR)
        key = _resolve_signing_key(log_dir, self.signing_key)
        body = self._snapshot_body()
        digest, sig = _compute_snapshot_digests(body, key)
        payload = {
            **body,
            "snapshot_sha256": digest,
            "signature": sig,
        }
        _atomic_write_json(self._snapshot_path(), payload)
        self.snapshot_sha256 = digest
        self.signature = sig
        self.signature_verified = True

    @classmethod
    def _verify_snapshot_payload(
        cls,
        data: dict[str, Any],
        *,
        signing_key: bytes,
    ) -> bool:
        """Verify v2 digest and HMAC-SHA256 signature; allow unsigned legacy v1."""
        has_v2_fields = any(
            k in data for k in ("schema", "snapshot_sha256", "signature")
        )
        if not has_v2_fields:
            return False

        if data.get("schema") != SNAPSHOT_SCHEMA:
            raise SnapshotIntegrityError(
                f"Unsupported rollback snapshot schema: {data.get('schema')!r}"
            )
        stored_sha = data.get("snapshot_sha256")
        stored_sig = data.get("signature")
        if not isinstance(stored_sha, str) or not isinstance(stored_sig, str):
            raise SnapshotIntegrityError("Missing snapshot_sha256 or signature")

        body = {
            k: v
            for k, v in data.items()
            if k not in ("snapshot_sha256", "signature")
        }
        expected_sha, expected_sig = _compute_snapshot_digests(body, signing_key)
        if not hmac.compare_digest(stored_sha, expected_sha):
            raise SnapshotIntegrityError("Snapshot SHA-256 digest mismatch")
        if not hmac.compare_digest(stored_sig, expected_sig):
            raise SnapshotIntegrityError("Snapshot HMAC-SHA256 signature mismatch")
        return True

    @classmethod
    def load(
        cls,
        session_id: str,
        *,
        signing_key: bytes | str | None = None,
        verify: bool = True,
    ) -> RollbackSession:
        """Load a persisted session and verify its cryptographic signature when present."""
        clean_id = _validate_session_id(session_id)
        log_dir = Path(cls.LOG_DIR)
        path = log_dir / f"{clean_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Rollback session '{clean_id}' not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SnapshotIntegrityError(
                f"Corrupted rollback snapshot JSON for '{clean_id}'"
            ) from exc
        if not isinstance(data, dict):
            raise SnapshotIntegrityError(
                f"Invalid rollback snapshot root for '{clean_id}'"
            )

        verified = False
        if verify:
            key = _resolve_signing_key(log_dir, signing_key)
            verified = cls._verify_snapshot_payload(data, signing_key=key)

        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise SnapshotIntegrityError("Invalid rollback entries payload")

        session = cls(
            session_id=str(data["session_id"]),
            created_at=str(data["created_at"]),
            signing_key=signing_key,
        )
        session.entries = [RollbackEntry(**entry) for entry in raw_entries]
        session.snapshot_sha256 = str(data.get("snapshot_sha256", ""))
        session.signature = str(data.get("signature", ""))
        session.signature_verified = verified
        return session

    @classmethod
    def recover(
        cls,
        session_id: str,
        *,
        signing_key: bytes | str | None = None,
    ) -> RollbackSession:
        """Recover a session after an interrupted write or mid-operation crash."""
        clean_id = _validate_session_id(session_id)
        log_dir = Path(cls.LOG_DIR)
        snapshot_path = log_dir / f"{clean_id}.json"
        journal_path = log_dir / f"{clean_id}.journal.json"

        # Clean up any orphaned atomic-write temp files for this session.
        if log_dir.exists():
            for tmp_file in log_dir.glob(f".{clean_id}.*.tmp"):
                with contextlib.suppress(OSError):
                    tmp_file.unlink()

        key = _resolve_signing_key(log_dir, signing_key)
        session: RollbackSession | None = None
        if snapshot_path.exists():
            session = cls.load(clean_id, signing_key=key, verify=True)

        if journal_path.exists():
            try:
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SnapshotIntegrityError(
                    f"Corrupted crash journal for '{clean_id}'"
                ) from exc
            if not isinstance(journal, dict) or journal.get("schema") != JOURNAL_SCHEMA:
                raise SnapshotIntegrityError(
                    f"Invalid crash journal schema for '{clean_id}'"
                )
            journal_body = {
                k: v
                for k, v in journal.items()
                if k not in ("journal_sha256", "signature")
            }
            exp_sha, exp_sig = _compute_snapshot_digests(journal_body, key)
            if not (
                hmac.compare_digest(str(journal.get("journal_sha256", "")), exp_sha)
                and hmac.compare_digest(str(journal.get("signature", "")), exp_sig)
            ):
                raise SnapshotIntegrityError(
                    f"Crash journal signature mismatch for '{clean_id}'"
                )

            if session is None:
                session = cls(
                    session_id=clean_id,
                    created_at=str(journal.get("created_at") or datetime.now().isoformat()),
                    signing_key=key,
                )

            prior_count = int(journal.get("prior_entry_count", 0))
            if len(session.entries) <= prior_count:
                session.entries.append(
                    RollbackEntry(
                        timestamp=str(
                            journal.get("started_at") or datetime.now().isoformat()
                        ),
                        command=str(journal.get("command", "")),
                        rollback_command=journal.get("rollback_command"),
                        stdout="",
                        stderr=(
                            "Interrupted before completion; recovered from signed "
                            "pre-execution crash journal."
                        ),
                        success=False,
                        exit_code=-1,
                        status="uncertain_interrupted",
                    )
                )
            session._save()
            with contextlib.suppress(OSError):
                journal_path.unlink()

        if session is None:
            raise FileNotFoundError(
                f"Neither snapshot nor crash journal found for '{clean_id}'"
            )
        return session

    @classmethod
    def list_sessions(cls, limit: int = 20) -> list[dict[str, Any]]:
        """List recent rollback sessions, skipping internal journal files."""
        log_dir = Path(cls.LOG_DIR)
        if not log_dir.exists():
            return []
        files = sorted(
            (
                f
                for f in log_dir.glob("*.json")
                if not f.name.endswith(".journal.json")
            ),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        sessions: list[dict[str, Any]] = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                entries = data["entries"]
                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "operations": len(entries),
                        "rollbackable": sum(
                            1
                            for e in entries
                            if e.get("rollback_command") and e.get("success")
                        ),
                        "interrupted": sum(
                            1
                            for e in entries
                            if e.get("status") == "uncertain_interrupted"
                        ),
                        "signed": bool(data.get("signature")),
                    }
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                continue
        return sessions
