"""Durable input-bound idempotency journal and verified receipts for FixOS MCP (#163).

Provides:
- Input-bound idempotency (`request_id` -> `(operation_id, registry_digest, input_digest)`)
- Single-flight lock (`threading.Lock` + POSIX `fcntl.flock`) preventing concurrent double effects
- Pre-effect atomic journal (`<req_id>.journal.json`) transitioning to `state="uncertain"` after crash
- Atomic fsync+replace receipt persistence (`<req_id>.json`) with UUIDv5 URN, correlation ID, target,
  timestamps, read-back verification summary, and verifiable `receipt_hash`
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import threading
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA = "wellmanifest.mcp/task-receipt/v1"
JOURNAL_SCHEMA = "wellmanifest.mcp/task-journal/v1"
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_RECEIPT_URN_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

_LOCKS_GUARD = threading.Lock()
_IN_PROCESS_LOCKS: dict[str, threading.Lock] = {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def validated_request_id(request_id: str) -> str:
    """Return a bounded portable receipt identifier, rejecting traversal or path separators."""
    clean_id = (request_id or "").strip()
    if not _REQUEST_ID_RE.fullmatch(clean_id) or ".." in clean_id:
        raise ValueError("invalid_request_id")
    return clean_id


def receipt_urn_for(request_id: str) -> str:
    """Derive deterministic RFC 4122 UUIDv5 URN for a receipt."""
    derived = uuid.uuid5(
        _RECEIPT_URN_NAMESPACE,
        f"https://wellmanifest.org/semcod/fixos/mcp-receipt/{request_id}",
    )
    return f"urn:uuid:{derived}"


def compute_receipt_hash(receipt_without_hash: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in receipt_without_hash.items()
        if k not in ("receipt_hash", "found", "replayed", "valid")
    }
    return canonical_digest(body)


def verify_receipt_integrity(receipt: Mapping[str, Any]) -> bool:
    stored = receipt.get("receipt_hash")
    if not isinstance(stored, str) or len(stored) != 64:
        return False
    return compute_receipt_hash(receipt) == stored


def _thread_lock_for(lock_key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _IN_PROCESS_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            _IN_PROCESS_LOCKS[lock_key] = lock
        return lock


@contextlib.contextmanager
def _single_flight_lock(base_dir: Path, req_id: str, *, non_blocking: bool = False):
    base_dir.mkdir(parents=True, exist_ok=True)
    lock_path = base_dir / f"{req_id}.lock"
    tlock = _thread_lock_for(str(lock_path.resolve()))
    acquired = tlock.acquire(blocking=not non_blocking)
    if not acquired:
        raise BlockingIOError("request_in_flight")
    fd = -1
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if non_blocking else 0)
        fcntl.flock(fd, flags)
        yield
    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                os.close(fd)
        tlock.release()


def atomic_write_json(target_path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically write JSON via temp file + flush + fsync + os.replace."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.parent / f".{target_path.name}.{uuid.uuid4().hex}.tmp"
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target_path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            if tmp_path.exists():
                tmp_path.unlink()
        raise RuntimeError(f"RECEIPT_WRITE_FAILED: {exc}") from exc


def _load_json_strict(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("CORRUPTED_RECEIPT") from exc
    if type(raw) is not dict:
        raise ValueError("CORRUPTED_RECEIPT")
    return raw


def _recover_interrupted_journal(
    journal_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    """Convert an orphaned pre-effect journal into an atomic uncertain receipt."""
    try:
        jdata = _load_json_strict(journal_path)
    except ValueError:
        jdata = {}

    req_id = str(jdata.get("request_id") or receipt_path.stem)
    uncertain: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "receipt_urn": jdata.get("receipt_urn") or receipt_urn_for(req_id),
        "request_id": req_id,
        "correlation_id": jdata.get("correlation_id") or f"corr-{req_id}",
        "operation_id": jdata.get("operation_id", "fixos://cleanup/auto"),
        "effect": jdata.get("effect", "mutate"),
        "dry_run": bool(jdata.get("dry_run", False)),
        "state": "uncertain",
        "interrupted": True,
        "started_at": jdata.get("started_at") or utc_now_iso(),
        "completed_at": utc_now_iso(),
        "registry_digest": jdata.get("registry_digest", ""),
        "input_digest": jdata.get("input_digest", ""),
        "target": jdata.get("target") or {"host": "local", "root": "/"},
        "readback": {
            "verified": False,
            "reason": "interrupted_in_flight_journal",
        },
        "actions": [],
    }
    uncertain["receipt_hash"] = compute_receipt_hash(uncertain)
    atomic_write_json(receipt_path, uncertain)
    with contextlib.suppress(OSError):
        journal_path.unlink()
    return uncertain


def _assert_binding_matches(
    stored: Mapping[str, Any],
    *,
    operation_id: str,
    registry_digest: str,
    input_digest: str,
) -> None:
    if (
        stored.get("operation_id") != operation_id
        or stored.get("registry_digest") != registry_digest
        or stored.get("input_digest") != input_digest
    ):
        raise ValueError("IDEMPOTENCY_CONFLICT")


def read_durable_receipt(
    request_id: str,
    *,
    base_dir: Path,
) -> dict[str, Any]:
    """Read back a receipt or transition an orphaned journal to uncertain without side effects."""
    receipt_path = base_dir / f"{request_id}.json"
    journal_path = base_dir / f"{request_id}.journal.json"

    if receipt_path.is_file():
        try:
            data = _load_json_strict(receipt_path)
        except ValueError:
            return {
                "schema": RECEIPT_SCHEMA,
                "found": True,
                "valid": False,
                "state": "uncertain",
                "request_id": request_id,
                "error": "CORRUPTED_RECEIPT",
            }
        if not verify_receipt_integrity(data):
            return {
                "schema": RECEIPT_SCHEMA,
                "found": True,
                "valid": False,
                "state": "uncertain",
                "request_id": request_id,
                "error": "CORRUPTED_RECEIPT",
            }
        return {**data, "found": True, "valid": True, "replayed": True}

    if journal_path.is_file():
        try:
            with _single_flight_lock(base_dir, request_id, non_blocking=True):
                if receipt_path.is_file():
                    data = _load_json_strict(receipt_path)
                    valid = verify_receipt_integrity(data)
                    return {**data, "found": True, "valid": valid, "replayed": True}
                if journal_path.is_file():
                    recovered = _recover_interrupted_journal(journal_path, receipt_path)
                    return {**recovered, "found": True, "valid": True, "replayed": True}
        except BlockingIOError:
            return {
                "schema": RECEIPT_SCHEMA,
                "found": True,
                "valid": True,
                "state": "in_progress",
                "request_id": request_id,
                "replayed": False,
            }

    return {
        "schema": RECEIPT_SCHEMA,
        "found": False,
        "request_id": request_id,
    }


def execute_with_durable_journal(
    *,
    base_dir: Path,
    request_id: str,
    correlation_id: str,
    operation_id: str,
    effect: str,
    dry_run: bool,
    registry_digest: str,
    input_digest: str,
    target: Mapping[str, Any],
    authorizer: Callable[[], dict[str, Any] | None] | None = None,
    runner: Callable[[str], tuple[dict[str, Any], Exception | None]],
) -> dict[str, Any]:
    """Run an operation single-flight with input-bound idempotency, pre-effect journal, and atomic receipt."""
    receipt_path = base_dir / f"{request_id}.json"
    journal_path = base_dir / f"{request_id}.journal.json"

    with _single_flight_lock(base_dir, request_id, non_blocking=False):
        if receipt_path.is_file():
            stored = _load_json_strict(receipt_path)
            if not verify_receipt_integrity(stored):
                raise ValueError("CORRUPTED_RECEIPT")
            _assert_binding_matches(
                stored,
                operation_id=operation_id,
                registry_digest=registry_digest,
                input_digest=input_digest,
            )
            return {**stored, "found": True, "replayed": True}

        if journal_path.is_file():
            recovered = _recover_interrupted_journal(journal_path, receipt_path)
            _assert_binding_matches(
                recovered,
                operation_id=operation_id,
                registry_digest=registry_digest,
                input_digest=input_digest,
            )
            return {**recovered, "found": True, "replayed": True}

        auth_meta = authorizer() if authorizer is not None else None

        started_at = utc_now_iso()
        r_urn = receipt_urn_for(request_id)
        corr = correlation_id or f"corr-{request_id}"

        journal_doc: dict[str, Any] = {
            "schema": JOURNAL_SCHEMA,
            "receipt_urn": r_urn,
            "request_id": request_id,
            "correlation_id": corr,
            "operation_id": operation_id,
            "effect": effect,
            "dry_run": dry_run,
            "state": "in_progress",
            "started_at": started_at,
            "registry_digest": registry_digest,
            "input_digest": input_digest,
            "target": dict(target),
        }
        if auth_meta:
            journal_doc["authorization"] = auth_meta
        atomic_write_json(journal_path, journal_doc)

        effect_body, raised_exc = runner(started_at)
        completed_at = utc_now_iso()

        receipt: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "receipt_urn": r_urn,
            "request_id": request_id,
            "correlation_id": corr,
            "operation_id": operation_id,
            "effect": effect,
            "dry_run": dry_run,
            "started_at": started_at,
            "completed_at": completed_at,
            "registry_digest": registry_digest,
            "input_digest": input_digest,
            "target": dict(target),
            **effect_body,
        }
        if auth_meta:
            receipt["authorization"] = auth_meta
        receipt["receipt_hash"] = compute_receipt_hash(receipt)
        atomic_write_json(receipt_path, receipt)
        with contextlib.suppress(OSError):
            journal_path.unlink()

        if raised_exc is not None:
            raise raised_exc
        return {**receipt, "found": True, "replayed": False}
