"""MCP URN Resource Surface (`resources/list`, `resources/templates/list`, `resources/read`) (#165).

Identifies all readable resources via standard IETF RFC 4122 `urn:uuid:<uuid>` URNs
paired with explicit `_meta.resourceType` descriptors, strictly distinguishing resource
identity (URN) from process/action identity (`fixos://...` URI). Reading a resource is
guaranteed side-effect-free and never triggers cleanup or process re-execution.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fixos.poa_registry import OWNER_REPOSITORY, export_mcp_registry_v1

_URN_UUID_RE = re.compile(
    r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_RESOURCE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

CATALOG_RESOURCE_URN = (
    f"urn:uuid:{uuid.uuid5(_RESOURCE_NS, 'https://wellmanifest.org/semcod/fixos/resource/catalog-v1')}"
)
QUICK_SNAPSHOT_RESOURCE_URN = (
    f"urn:uuid:{uuid.uuid5(_RESOURCE_NS, 'https://wellmanifest.org/semcod/fixos/resource/quick-snapshot')}"
)
FORBIDDEN_INTERNAL_URN = (
    f"urn:uuid:{uuid.uuid5(_RESOURCE_NS, 'https://wellmanifest.org/semcod/fixos/resource/internal-credentials')}"
)

DEFAULT_PAGE_SIZE = 10
DEFAULT_RETENTION_DAYS = 30
ALLOWED_RESOURCE_TYPES = frozenset(
    {
        "fixos.mcp.registry-v1",
        "fixos.snapshot.quick",
        "fixos.poa.plan",
        "fixos.mcp.receipt",
    }
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        norm = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        return datetime.fromisoformat(norm).astimezone(timezone.utc)
    except ValueError:
        return None


def _within_retention(
    timestamp_str: str,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> bool:
    if retention_days <= 0:
        return False
    parsed = _parse_iso(timestamp_str)
    if parsed is None:
        return True
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return (ref_now - parsed) <= timedelta(days=retention_days)


def _validate_resource_output_schema(resource_type: str, doc: Mapping[str, Any]) -> None:
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise PermissionError("FORBIDDEN_RESOURCE_SCOPE")
    if resource_type == "fixos.mcp.registry-v1":
        if doc.get("schema") != "wellmanifest.mcp/registry/v1" or not isinstance(
            doc.get("operations"), list
        ):
            raise ValueError("RESOURCE_OUTPUT_SCHEMA_INVALID")
    elif resource_type == "fixos.snapshot.quick":
        if doc.get("resource_type") != "fixos.snapshot.quick" or not isinstance(
            doc.get("snapshot"), Mapping
        ):
            raise ValueError("RESOURCE_OUTPUT_SCHEMA_INVALID")
    elif resource_type == "fixos.poa.plan":
        if doc.get("schema") != "wellmanifest.poa/minimal-plan/v1" or "plan_hash" not in doc:
            raise ValueError("RESOURCE_OUTPUT_SCHEMA_INVALID")
    elif resource_type == "fixos.mcp.receipt" and (
        doc.get("schema") != "wellmanifest.mcp/task-receipt/v1" or "request_id" not in doc
    ):
        raise ValueError("RESOURCE_OUTPUT_SCHEMA_INVALID")


def mcp_resource_templates_list() -> dict[str, Any]:
    """Return MCP resources/templates/list descriptor."""
    return {
        "resourceTemplates": [
            {
                "uriTemplate": "urn:uuid:{uuid}",
                "name": "FixOS Canonical URN Resource",
                "description": (
                    "Read-only FixOS resource addressed by standard IETF RFC 4122 urn:uuid:<uuid> "
                    "covering registry catalog, quick telemetry snapshot, POA plans, and execution receipts."
                ),
                "mimeType": "application/json",
                "_meta": {
                    "owner": OWNER_REPOSITORY,
                    "allowedResourceTypes": sorted(ALLOWED_RESOURCE_TYPES),
                },
            }
        ]
    }


def _collect_all_resources(
    *,
    receipts_dir: Path,
    grants_dir: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> list[tuple[dict[str, Any], Path | None, str]]:
    """Return ordered list of (descriptor, backing_path_or_none, resource_type)."""
    items: list[tuple[dict[str, Any], Path | None, str]] = [
        (
            {
                "uri": CATALOG_RESOURCE_URN,
                "name": "fixos-mcp-registry-v1",
                "title": "FixOS Canonical POA/MCP Registry (v1)",
                "description": "Read-only wellmanifest.mcp/registry/v1 capability catalog.",
                "mimeType": "application/json",
                "_meta": {"resourceType": "fixos.mcp.registry-v1", "owner": OWNER_REPOSITORY},
            },
            None,
            "fixos.mcp.registry-v1",
        ),
        (
            {
                "uri": QUICK_SNAPSHOT_RESOURCE_URN,
                "name": "fixos-quick-snapshot",
                "title": "FixOS Read-Only Host Telemetry Snapshot",
                "description": "Pure read-only CPU, RAM, and disk snapshot without side effects.",
                "mimeType": "application/json",
                "_meta": {"resourceType": "fixos.snapshot.quick", "owner": OWNER_REPOSITORY},
            },
            None,
            "fixos.snapshot.quick",
        ),
    ]

    if grants_dir.is_dir():
        for pfile in sorted(grants_dir.glob("plan-*.json")):
            if not pfile.is_file() or pfile.is_symlink():
                continue
            try:
                pdoc = json.loads(pfile.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if type(pdoc) is not dict:
                continue
            p_urn = pdoc.get("plan_urn")
            obs = pdoc.get("observation") if isinstance(pdoc.get("observation"), Mapping) else {}
            observed_at = str(obs.get("observed_at", ""))
            if (
                isinstance(p_urn, str)
                and _URN_UUID_RE.fullmatch(p_urn)
                and _within_retention(observed_at, retention_days=retention_days, now=now)
            ):
                items.append(
                    (
                        {
                            "uri": p_urn,
                            "name": str(pdoc.get("plan_id") or pfile.stem),
                            "title": f"POA Plan {pdoc.get('plan_id', pfile.stem)}",
                            "description": f"Typed POA plan for {pdoc.get('operation_id', '')}",
                            "mimeType": "application/json",
                            "_meta": {
                                "resourceType": "fixos.poa.plan",
                                "owner": OWNER_REPOSITORY,
                                "planHash": pdoc.get("plan_hash", ""),
                            },
                        },
                        pfile,
                        "fixos.poa.plan",
                    )
                )

    if receipts_dir.is_dir():
        for rfile in sorted(receipts_dir.glob("*.json")):
            if rfile.name.endswith(".journal.json") or not rfile.is_file() or rfile.is_symlink():
                continue
            try:
                rdoc = json.loads(rfile.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if type(rdoc) is not dict:
                continue
            r_urn = rdoc.get("receipt_urn")
            completed_at = str(rdoc.get("completed_at") or rdoc.get("started_at") or "")
            if (
                isinstance(r_urn, str)
                and _URN_UUID_RE.fullmatch(r_urn)
                and _within_retention(completed_at, retention_days=retention_days, now=now)
            ):
                items.append(
                    (
                        {
                            "uri": r_urn,
                            "name": f"receipt-{rdoc.get('request_id', rfile.stem)}",
                            "title": f"Execution Receipt {rdoc.get('request_id', rfile.stem)}",
                            "description": (
                                f"Durable receipt ({rdoc.get('state', 'unknown')}) "
                                f"for {rdoc.get('operation_id', '')}"
                            ),
                            "mimeType": "application/json",
                            "_meta": {
                                "resourceType": "fixos.mcp.receipt",
                                "owner": OWNER_REPOSITORY,
                                "state": rdoc.get("state", ""),
                            },
                        },
                        rfile,
                        "fixos.mcp.receipt",
                    )
                )

    return items


def mcp_resources_list(
    *,
    cursor: str | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    receipts_dir: Path,
    grants_dir: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """List readable URN resources with deterministic cursor pagination."""
    if page_size < 1 or page_size > 100:
        raise ValueError("INVALID_PAGE_SIZE")
    start_idx = 0
    if cursor is not None and cursor != "":
        if not isinstance(cursor, str) or not cursor.isdigit():
            raise ValueError("INVALID_CURSOR")
        start_idx = int(cursor)

    all_items = _collect_all_resources(
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
        retention_days=retention_days,
        now=now,
    )
    if start_idx > len(all_items):
        raise ValueError("INVALID_CURSOR")

    sliced = [desc for desc, _, _ in all_items[start_idx : start_idx + page_size]]
    result: dict[str, Any] = {"resources": sliced}
    if start_idx + page_size < len(all_items):
        result["nextCursor"] = str(start_idx + page_size)
    return result


def mcp_resources_read(
    uri: str,
    *,
    receipts_dir: Path,
    grants_dir: Path,
    quick_snapshot_loader: Callable[[], dict[str, Any]],
    allowed_types: frozenset[str] = ALLOWED_RESOURCE_TYPES,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read a URN resource without side effects, enforcing URN format, scope, retention, and schema."""
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("INVALID_RESOURCE_URN")
    clean_uri = uri.strip()
    if "://" in clean_uri:
        raise ValueError("ACTION_URI_NOT_READABLE_AS_RESOURCE")
    if not _URN_UUID_RE.fullmatch(clean_uri):
        raise ValueError("INVALID_RESOURCE_URN")
    if clean_uri == FORBIDDEN_INTERNAL_URN:
        raise PermissionError("FORBIDDEN_RESOURCE_SCOPE")

    payload: dict[str, Any] | None = None
    rtype = ""

    if clean_uri == CATALOG_RESOURCE_URN:
        rtype = "fixos.mcp.registry-v1"
        payload = export_mcp_registry_v1(now=now)
    elif clean_uri == QUICK_SNAPSHOT_RESOURCE_URN:
        rtype = "fixos.snapshot.quick"
        payload = {
            "resource_urn": QUICK_SNAPSHOT_RESOURCE_URN,
            "resource_type": "fixos.snapshot.quick",
            "snapshot": quick_snapshot_loader(),
        }
    else:
        if grants_dir.is_dir():
            for pfile in sorted(grants_dir.glob("plan-*.json")):
                if not pfile.is_file() or pfile.is_symlink():
                    continue
                try:
                    pdoc = json.loads(pfile.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if type(pdoc) is dict and pdoc.get("plan_urn") == clean_uri:
                    obs = (
                        pdoc.get("observation")
                        if isinstance(pdoc.get("observation"), Mapping)
                        else {}
                    )
                    if not _within_retention(
                        str(obs.get("observed_at", "")),
                        retention_days=retention_days,
                        now=now,
                    ):
                        raise ValueError("RESOURCE_RETENTION_EXPIRED")
                    rtype = "fixos.poa.plan"
                    payload = pdoc
                    break

        if payload is None and receipts_dir.is_dir():
            for rfile in sorted(receipts_dir.glob("*.json")):
                if rfile.name.endswith(".journal.json") or not rfile.is_file() or rfile.is_symlink():
                    continue
                try:
                    rdoc = json.loads(rfile.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if type(rdoc) is dict and rdoc.get("receipt_urn") == clean_uri:
                    ts = str(rdoc.get("completed_at") or rdoc.get("started_at") or "")
                    if not _within_retention(ts, retention_days=retention_days, now=now):
                        raise ValueError("RESOURCE_RETENTION_EXPIRED")
                    rtype = "fixos.mcp.receipt"
                    payload = rdoc
                    break

    if payload is None:
        raise KeyError("UNKNOWN_RESOURCE_URN")
    if rtype not in allowed_types:
        raise PermissionError("FORBIDDEN_RESOURCE_SCOPE")
    _validate_resource_output_schema(rtype, payload)

    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    return {
        "contents": [
            {
                "uri": clean_uri,
                "mimeType": "application/json",
                "text": serialized,
                "_meta": {
                    "resourceType": rtype,
                    "sha256": _sha256_text(serialized),
                },
            }
        ]
    }
