"""Fail-open uritime.urtlog.record/v2 telemetry emitter for fixOS diagnostics.

Writes structured JSONL records into ``<state_dir>/events.jsonl`` only when
``FIXOS_URTLOG_STATE_DIR`` or ``URTLOG_STATE_DIR`` (or an explicit ``state_dir``)
is configured. Never raises and adds zero external runtime dependencies.
"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

URTLOG_RECORD_SCHEMA = "uritime.urtlog.record/v2"
FIXOS_ACTOR = "semcod:fixos"


def resolve_urtlog_state_dir(state_dir: str | Path | None = None) -> Path | None:
    """Return configured URTLog state directory, or ``None`` if disabled."""
    if state_dir is not None:
        raw = str(state_dir).strip()
        return Path(raw).expanduser() if raw else None
    raw_env = (
        os.environ.get("FIXOS_URTLOG_STATE_DIR")
        or os.environ.get("URTLOG_STATE_DIR")
        or ""
    ).strip()
    return Path(raw_env).expanduser() if raw_env else None


def emit_urtlog_record(
    *,
    action: str,
    uri: str,
    status: str = "succeeded",
    kind: str = "log",
    stage: str = "completed",
    details: dict[str, Any] | None = None,
    state_dir: str | Path | None = None,
) -> bool:
    """Append one ``uritime.urtlog.record/v2`` record to ``events.jsonl``."""
    target_dir = resolve_urtlog_state_dir(state_dir)
    if target_dir is None:
        return False

    record: dict[str, Any] = {
        "schema": URTLOG_RECORD_SCHEMA,
        "kind": kind,
        "stage": stage,
        "status": status,
        "actor": FIXOS_ACTOR,
        "action": action,
        "uri": uri,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "host": socket.gethostname(),
    }
    if details:
        record["details"] = details

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        events_path = target_dir / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def emit_cleanup_veto(
    *,
    target: str,
    verdict: str,
    veto_codes: tuple[str, ...] | list[str],
    reasons: tuple[str, ...] | list[str],
    state_dir: str | Path | None = None,
) -> bool:
    """Emit a structured URTLog event when a hard cleanup veto protects a workspace."""
    return emit_urtlog_record(
        action="fixos.cleanup_veto",
        uri="proc://semcod/fixos/project-scanner/veto/v1",
        status="blocked",
        details={
            "target": target,
            "verdict": verdict,
            "veto_codes": list(veto_codes),
            "reasons": list(reasons),
        },
        state_dir=state_dir,
    )


def emit_cleanup_summary(
    *,
    mode: str,
    reclaimed_bytes: int,
    steps: list[str],
    dry_run: bool = False,
    errors: list[str] | None = None,
    state_dir: str | Path | None = None,
) -> bool:
    """Emit a structured URTLog event summarizing a fixOS cleanup run."""
    return emit_urtlog_record(
        action="fixos.cleanup_summary",
        uri="proc://semcod/fixos/cleanup/v1",
        status="failed" if errors else "succeeded",
        details={
            "mode": mode,
            "reclaimed_bytes": int(reclaimed_bytes),
            "steps": list(steps),
            "dry_run": bool(dry_run),
            "errors": list(errors or []),
        },
        state_dir=state_dir,
    )
