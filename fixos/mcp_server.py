"""Model Context Protocol (MCP) Server for FixOS.

Conforms to wellmanifest/mcp (MCP URI Reuse & Operation Contract) and
wellmanifest/nl-dsl-llm (Tripartite NL -> Canonical URI/DSL -> Execution).

Separates pure read diagnostics from effectful cleanup operations, binds
mutating executions to catalog digests and durable request receipts, and
supports both stdlib JSON-RPC 2.0 over stdio and optional FastMCP.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import uuid
from collections.abc import Mapping
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from fixos import __version__
from fixos.mcp_receipts import (
    RECEIPT_SCHEMA,
    execute_with_durable_journal,
    read_durable_receipt,
    validated_request_id,
)
from fixos.poa_grants import (
    cleanup_poa_input,
    cleanup_poa_target,
    jcs_sha256,
    verify_and_consume_poa_grant,
)
from fixos.poa_registry import (
    DEFAULT_REGISTRY_TTL_SECONDS,
    LEGACY_CATALOG_SCHEMA,
    catalog_static_digest,
    deployment_revision,
    export_mcp_registry_v1,
    operations_catalog_projection,
    validate_timestamp_freshness,
)

CATALOG_SCHEMA = LEGACY_CATALOG_SCHEMA
PLAN_SCHEMA = "wellmanifest.nl-dsl-llm/task-plan/v1"
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

OPERATIONS_CATALOG: tuple[dict[str, Any], ...] = operations_catalog_projection()


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_arguments(schema: Mapping[str, Any], value: Any, path: str = "arguments") -> None:
    """Validate the object/primitive JSON Schema subset used by this catalog.

    This is a bounded catalog validator, not a general JSON Schema engine.
    Unsupported constraints fail closed rather than silently weakening a tool.
    Errors contain only schema-owned paths, never rejected values or keys.
    """
    supported = {
        "type", "properties", "required", "additionalProperties", "default",
        "description", "minLength", "maxLength", "minimum", "maximum",
    }
    if set(schema) - supported:
        raise ValueError("UNSUPPORTED_INPUT_SCHEMA")
    kind = schema.get("type")
    valid_type = {
        "object": isinstance(value, Mapping),
        "string": isinstance(value, str),
        "boolean": type(value) is bool,
        "number": type(value) in (int, float),
        "integer": type(value) is int,
    }
    if kind not in valid_type:
        raise ValueError("UNSUPPORTED_INPUT_SCHEMA")
    if not valid_type[kind]:
        raise ValueError(f"INVALID_ARGUMENTS: {path}: expected {kind}")
    if kind == "object":
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError(f"INVALID_ARGUMENTS: {path}: missing required field")
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ValueError(f"INVALID_ARGUMENTS: {path}: unknown field")
        for key, child in properties.items():
            if key in value:
                _validate_arguments(child, value[key], f"{path}.{key}")
    elif kind in ("number", "integer"):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"INVALID_ARGUMENTS: {path}: expected finite number")
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            raise ValueError(f"INVALID_ARGUMENTS: {path}: out of range")
    elif kind == "string" and (
        len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value))
    ):
        raise ValueError(f"INVALID_ARGUMENTS: {path}: invalid length")


def catalog_digest() -> str:
    """Return deterministic SHA-256 digest of the registered MCP operations."""
    return catalog_static_digest(OPERATIONS_CATALOG)


def _receipts_dir(custom_dir: str | Path | None = None) -> Path:
    if custom_dir:
        base = Path(custom_dir)
    else:
        env_dir = os.environ.get("FIXOS_MCP_RECEIPTS_DIR")
        base = Path(env_dir) if env_dir else Path.home() / ".local" / "state" / "fixos" / "mcp-receipts"
    base.mkdir(parents=True, exist_ok=True)
    return base


def registry_search(
    query: str = "",
    limit: int = 50,
    *,
    strict_v1: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Search registered FixOS MCP URI operations (wellmanifest/mcp discovery)."""
    q = (query or "").strip().lower()
    bounded_limit = max(1, min(int(limit), 50))
    if strict_v1:
        v1 = export_mcp_registry_v1(now=now, ttl_seconds=DEFAULT_REGISTRY_TTL_SECONDS)
        ops = [
            op
            for op in v1["operations"]
            if not q
            or q in f"{op['id']} {op['uri']} {op['description']}".lower()
            or any(tok in f"{op['id']} {op['uri']} {op['description']}".lower() for tok in q.split())
        ][:bounded_limit]
        return {**v1, "operations": ops}

    v1_envelope = export_mcp_registry_v1(now=now, ttl_seconds=DEFAULT_REGISTRY_TTL_SECONDS)
    expires_at = v1_envelope["expiresAt"]
    matches: list[dict[str, Any]] = []
    for op in OPERATIONS_CATALOG:
        haystack = (
            f"{op.get('id', '')} {op['operation_id']} {op.get('tool_name', '')} "
            f"{op['title']} {op['description']}"
        ).lower()
        if not q or q in haystack or any(tok in haystack for tok in q.split()):
            matches.append({**dict(op), "expiresAt": expires_at})
        if len(matches) >= bounded_limit:
            break
    return {
        "schema": CATALOG_SCHEMA,
        "revision": deployment_revision(),
        "expiresAt": expires_at,
        "server": "fixos",
        "version": __version__,
        "registry_digest": catalog_digest(),
        "query": query,
        "count": len(matches),
        "operations": matches,
    }


def task_plan(task: str) -> dict[str, Any]:
    """Deterministically map natural language intent to a FixOS URI operation without executing it."""
    text = (task or "").strip()
    lower = text.lower()
    selected = OPERATIONS_CATALOG[0]
    confidence = 0.75

    if any(k in lower for k in ("wyczysc", "zwolnij", "cleanup", "clean", "prune", "auto", "usun")):
        selected = next(op for op in OPERATIONS_CATALOG if op["operation_id"] == "fixos://cleanup/auto")
        confidence = 0.92
    elif any(k in lower for k in ("projekt", "project", "venv", "node_modules", "tygodn", "7d", "state")):
        selected = next(op for op in OPERATIONS_CATALOG if op["operation_id"] == "fixos://diagnostics/projects")
        confidence = 0.90
    elif any(k in lower for k in ("dysk", "disk", "miejsce", "space", "cache", "rozmiar")):
        selected = next(op for op in OPERATIONS_CATALOG if op["operation_id"] == "fixos://diagnostics/disk")
        confidence = 0.88

    return {
        "schema": PLAN_SCHEMA,
        "task": text,
        "advisory": True,
        "grants_authority": False,
        "executable": False,
        "operation_id": selected["operation_id"],
        "tool_name": selected["tool_name"],
        "effect": selected["effect"],
        "confidence": confidence,
        "registry_digest": catalog_digest(),
    }


def run_fixos_quick() -> dict[str, Any]:
    """Execute read-only quick snapshot diagnostic."""
    from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

    snap = collect_quick_snapshot()
    return {
        "operation_id": "fixos://diagnostics/quick",
        "effect": "read",
        "snapshot": snap,
    }


def scan_user_cache_dirs() -> list[dict[str, Any]]:
    """Return top-level ~/.cache candidate dicts."""
    from fixos.cli._cleanup_space import _user_cache_candidates

    return [
        {
            "name": c.get("description", ""),
            "path": str(c.get("path", "")),
            "size_bytes": int(c.get("size_bytes", 0)),
            "safe": bool(c.get("safe", False)),
            "note": c.get("note", ""),
        }
        for c in _user_cache_candidates()
    ]


def scan_additional_safe_caches() -> list[dict[str, Any]]:
    """Return additional leaf safe cache candidate dicts."""
    from fixos.cli._auto_cleanup import additional_cache_candidates

    return [
        {
            "description": c.get("description", ""),
            "path": str(c.get("path", "")),
            "size_bytes": int(c.get("size_bytes", 0)),
            "note": c.get("note", ""),
        }
        for c in additional_cache_candidates()
    ]


def scan_build_and_package_caches(home_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return build and package cache candidate dicts (Cargo target/debug, ~/.npm/_cacache, conda pkgs)."""
    from fixos.cli._cleanup_space import _dir_size, _dir_sizes

    home = home_dir or Path.home()
    dirs_to_size: list[Path] = []
    seen_resolved: set[Path] = set()
    file_candidates: list[dict[str, Any]] = []

    github_root = home / "github"
    if github_root.is_dir():
        for pat in ("*/*/target/debug", "*/*/packages/*/target/debug"):
            for dbg in sorted(github_root.glob(pat)):
                if dbg.is_dir() and not dbg.is_symlink():
                    try:
                        real = dbg.resolve()
                    except OSError:
                        real = dbg
                    if real not in seen_resolved:
                        seen_resolved.add(real)
                        dirs_to_size.append(dbg)

    npm_cache = home / ".npm" / "_cacache"
    if npm_cache.is_dir() and not npm_cache.is_symlink():
        dirs_to_size.append(npm_cache)

    conda_pkgs = home / "miniconda3" / "pkgs"
    if conda_pkgs.is_dir():
        for ext in ("*.tar.bz2", "*.conda"):
            for archive in sorted(conda_pkgs.glob(ext)):
                try:
                    if archive.is_file() and not archive.is_symlink():
                        file_candidates.append(
                            {
                                "description": f"miniconda3/pkgs/{archive.name}",
                                "path": str(archive),
                                "size_bytes": archive.stat().st_size,
                                "note": "archiwum pakietu conda",
                            }
                        )
                except OSError:
                    continue

    sizes = _dir_sizes(dirs_to_size) if dirs_to_size else {}
    candidates: list[dict[str, Any]] = []
    for d in dirs_to_size:
        sz = sizes.get(str(d))
        if sz is None:
            sz = _dir_size(d)
        if sz <= 0:
            continue
        try:
            rel = str(d.relative_to(home))
        except ValueError:
            rel = str(d)
        candidates.append(
            {
                "description": f"~/{rel}",
                "path": str(d),
                "size_bytes": int(sz),
                "note": "regenerowalny cache kompilacji/pakietów",
            }
        )
    candidates.extend(file_candidates)
    candidates.sort(key=lambda item: (-item.get("size_bytes", 0), item["description"]))
    return candidates


def scan_unused_recent_project_artifacts(min_age_days: float = 7.0) -> list[dict[str, Any]]:
    """Return safe regenerable artifacts in developer projects unused for >= min_age_days."""
    from fixos.cli._cleanup_space import _scan_unused_projects

    days = max(1, int(min_age_days))
    return [
        {
            "description": c.get("description", ""),
            "path": str(c.get("path", "")),
            "project": str(c.get("project", "")),
            "artifact_name": c.get("artifact_name", ""),
            "ecosystem": c.get("ecosystem", ""),
            "age_days": float(c.get("age_days", 0.0)),
            "size_bytes": int(c.get("size_bytes", 0)),
            "note": c.get("note", ""),
        }
        for c in _scan_unused_projects(days=days)
    ]


def scan_stale_app_state_partitions(min_age_days: float = 7.0) -> list[dict[str, Any]]:
    """Return date-partitioned application state stores with partitions older than min_age_days."""
    from fixos.diagnostics.state_retention import scan_state_retention

    days = max(1, int(min_age_days))
    stores = scan_state_retention(days)
    return [
        {
            "path": str(store.path),
            "partitions": len(store.old_days),
            "oldest": str(store.oldest),
            "newest": str(store.newest),
            "kept_partitions": store.kept_days,
            "apparent_bytes": int(store.apparent_bytes),
            "size_bytes": int(store.reclaimable_bytes),
        }
        for store in stores
    ]


def run_fixos_scan_disk(path: str = "/") -> dict[str, Any]:
    """Execute read-only disk and safe cache inventory."""
    import shutil

    usage = shutil.disk_usage(path)
    user_caches = scan_user_cache_dirs()
    additional_caches = scan_additional_safe_caches()
    build_caches = scan_build_and_package_caches()

    safe_user_bytes = sum(int(c.get("size_bytes", 0)) for c in user_caches if c.get("safe"))
    additional_bytes = sum(int(c.get("size_bytes", 0)) for c in additional_caches)
    build_bytes = sum(int(c.get("size_bytes", 0)) for c in build_caches)

    return {
        "operation_id": "fixos://diagnostics/disk",
        "effect": "read",
        "path": path,
        "disk": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_percent": round(100.0 * usage.free / usage.total, 2) if usage.total else 0.0,
        },
        "reclaimable_summary": {
            "safe_user_cache_bytes": safe_user_bytes,
            "additional_safe_cache_bytes": additional_bytes,
            "build_and_package_cache_bytes": build_bytes,
            "total_safe_cache_bytes": safe_user_bytes + additional_bytes + build_bytes,
        },
        "candidates": {
            "user_cache_count": len(user_caches),
            "additional_cache_count": len(additional_caches),
            "build_cache_count": len(build_caches),
        },
    }


def run_fixos_scan_projects(min_age_days: float = 7.0) -> dict[str, Any]:
    """Execute read-only scan of stale developer project artifacts and date-partitioned state."""
    projects = scan_unused_recent_project_artifacts(min_age_days=float(min_age_days))
    partitions = scan_stale_app_state_partitions(min_age_days=float(min_age_days))
    proj_bytes = sum(int(item.get("size_bytes", 0)) for item in projects)
    part_bytes = sum(int(item.get("size_bytes", 0)) for item in partitions)

    return {
        "operation_id": "fixos://diagnostics/projects",
        "effect": "read",
        "min_age_days": float(min_age_days),
        "project_artifacts_count": len(projects),
        "project_artifacts_bytes": proj_bytes,
        "state_partitions_count": len(partitions),
        "state_partitions_bytes": part_bytes,
        "total_reclaimable_bytes": proj_bytes + part_bytes,
        "project_artifacts": projects[:50],
        "state_partitions": partitions[:50],
    }


def _validated_request_id(request_id: str) -> str:
    """Return a bounded portable receipt name, never a filesystem path."""
    return validated_request_id(request_id)


def task_status(request_id: str, *, receipts_dir: str | Path | None = None) -> dict[str, Any]:
    """Read back a durable execution receipt without re-running any effect (wellmanifest/mcp)."""
    clean_id = (request_id or "").strip()
    try:
        clean_id = _validated_request_id(clean_id)
    except ValueError:
        return {
            "schema": RECEIPT_SCHEMA,
            "found": False,
            "request_id": clean_id,
            "error": "invalid_request_id",
        }
    return read_durable_receipt(clean_id, base_dir=_receipts_dir(receipts_dir))


def _scan_cleanup_candidates(*, min_age_days: float, include_projects: bool) -> dict[str, list[dict[str, Any]]]:
    return {
        "user_caches": [c for c in scan_user_cache_dirs() if c.get("safe")],
        "add_caches": scan_additional_safe_caches(),
        "build_caches": scan_build_and_package_caches(),
        "proj_items": (
            scan_unused_recent_project_artifacts(min_age_days=float(min_age_days))
            if include_projects
            else []
        ),
        "part_items": (
            scan_stale_app_state_partitions(min_age_days=float(min_age_days))
            if include_projects
            else []
        ),
    }


def run_fixos_auto_cleanup(
    *,
    dry_run: bool = True,
    min_age_days: float = 7.0,
    include_projects: bool = True,
    request_id: str = "",
    registry_digest: str = "",
    plan_hash: str = "",
    grant_id: str = "",
    correlation_id: str = "",
    receipts_dir: str | Path | None = None,
    grants_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute bounded deterministic cleanup or dry-run preview with verified read-back and POA grant."""
    import shutil

    from fixos.cli._auto_cleanup import cleanup_additional_caches
    from fixos.cli._cleanup_space import (
        _cleanup_build_caches,
        _cleanup_projects_old,
        _cleanup_state_old,
        _cleanup_user_cache,
    )

    req_id = _validated_request_id(
        (request_id or "").strip() or f"fixos-mcp-{uuid.uuid4().hex[:12]}"
    )
    current_digest = catalog_digest()
    if dry_run and registry_digest and registry_digest != current_digest:
        raise ValueError("CATALOG_DIGEST_MISMATCH")

    norm_input = cleanup_poa_input(
        dry_run=bool(dry_run),
        min_age_days=float(min_age_days),
        include_projects=bool(include_projects),
    )
    input_digest = jcs_sha256(norm_input)
    target_desc = cleanup_poa_target(
        include_projects=bool(include_projects),
        min_age_days=float(min_age_days),
    )
    base_receipts = _receipts_dir(receipts_dir)

    def _authorize_mutation() -> dict[str, Any] | None:
        if dry_run:
            return None
        return verify_and_consume_poa_grant(
            grant_id=grant_id,
            plan_hash=plan_hash,
            operation_id="fixos://cleanup/auto",
            caller_registry_digest=registry_digest,
            current_registry_digest=current_digest,
            normalized_input=norm_input,
            target=target_desc,
            store_dir=grants_dir,
        )

    def _execute_cleanup(_started_at: str) -> tuple[dict[str, Any], Exception | None]:
        before_free = shutil.disk_usage("/").free
        before_scan = _scan_cleanup_candidates(
            min_age_days=float(min_age_days),
            include_projects=bool(include_projects),
        )
        user_caches = before_scan["user_caches"]
        add_caches = before_scan["add_caches"]
        build_caches = before_scan["build_caches"]
        proj_items = before_scan["proj_items"]
        part_items = before_scan["part_items"]

        planned_bytes = sum(
            int(item.get("size_bytes", 0))
            for group in before_scan.values()
            for item in group
        )
        planned_count = sum(len(group) for group in before_scan.values())

        actions_taken: list[str] = []
        helper_errors: list[Exception] = []
        error_messages: list[str] = []
        days_int = max(1, int(min_age_days))

        if not dry_run:
            steps: list[tuple[str, list[dict[str, Any]], Any]] = [
                (
                    "user_caches",
                    user_caches,
                    lambda: _cleanup_user_cache(
                        json_output=False, dry_run=False, list_only=False, yes=True
                    ),
                ),
                (
                    "additional_caches",
                    add_caches,
                    lambda: cleanup_additional_caches(dry_run=False, yes=True),
                ),
                (
                    "build_caches",
                    build_caches,
                    lambda: _cleanup_build_caches(
                        json_output=False,
                        dry_run=False,
                        list_only=False,
                        yes=True,
                        include_build_cache=True,
                        clean_state_old=False,
                        clean_projects_old=False,
                    ),
                ),
                (
                    "project_artifacts",
                    proj_items,
                    lambda: _cleanup_projects_old(
                        json_output=False,
                        dry_run=False,
                        list_only=False,
                        yes=True,
                        days=days_int,
                    ),
                ),
                (
                    "state_partitions",
                    part_items,
                    lambda: _cleanup_state_old(
                        json_output=False,
                        dry_run=False,
                        list_only=False,
                        yes=True,
                        days=days_int,
                    ),
                ),
            ]
            for label, items, invoke in steps:
                if not items:
                    continue
                try:
                    invoke()
                    actions_taken.append(f"{label}:{len(items)}")
                except Exception as exc:  # noqa: BLE001
                    helper_errors.append(exc)
                    error_messages.append(f"{label}:{exc}")

        after_free = shutil.disk_usage("/").free
        reclaimed_bytes = max(0, after_free - before_free) if not dry_run else 0

        if dry_run:
            state = "planned"
            readback: dict[str, Any] = {
                "verified": False,
                "reason": "dry_run",
                "planned_targets": planned_count,
                "remaining_targets": planned_count,
                "removed_targets": 0,
            }
        else:
            try:
                after_scan = _scan_cleanup_candidates(
                    min_age_days=float(min_age_days),
                    include_projects=bool(include_projects),
                )
                remaining_count = sum(len(group) for group in after_scan.values())
                removed_count = max(0, planned_count - remaining_count)
                readback = {
                    "verified": True,
                    "planned_targets": planned_count,
                    "remaining_targets": remaining_count,
                    "removed_targets": removed_count,
                }
                if (planned_count == 0 or remaining_count == 0) and not helper_errors:
                    state = "succeeded"
                elif removed_count > 0 and (remaining_count > 0 or helper_errors):
                    state = "partial"
                else:
                    state = "failed"
            except Exception as rb_exc:  # noqa: BLE001
                state = "uncertain"
                readback = {
                    "verified": False,
                    "reason": "readback_failed",
                    "error": str(rb_exc),
                    "planned_targets": planned_count,
                }

        body: dict[str, Any] = {
            "state": state,
            "planned_reclaimable_bytes": planned_bytes,
            "reclaimed_bytes": reclaimed_bytes,
            "free_bytes_before": before_free,
            "free_bytes_after": after_free,
            "actions": actions_taken,
            "readback": readback,
            "counts": {
                "safe_user_caches": len(user_caches),
                "additional_caches": len(add_caches),
                "build_caches": len(build_caches),
                "project_artifacts": len(proj_items),
                "state_partitions": len(part_items),
            },
        }
        if error_messages:
            body["errors"] = error_messages
        return body, (helper_errors[0] if helper_errors else None)

    return execute_with_durable_journal(
        base_dir=base_receipts,
        request_id=req_id,
        correlation_id=correlation_id,
        operation_id="fixos://cleanup/auto",
        effect="read" if dry_run else "mutate",
        dry_run=bool(dry_run),
        registry_digest=current_digest,
        input_digest=input_digest,
        target=target_desc,
        authorizer=_authorize_mutation,
        runner=_execute_cleanup,
    )


def task_execute(
    operation_id: str,
    payload: Mapping[str, Any] | None = None,
    *,
    registry_digest: str = "",
    request_id: str = "",
    plan_hash: str = "",
    grant_id: str = "",
    correlation_id: str = "",
    receipts_dir: str | Path | None = None,
    grants_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute a registered FixOS URI operation with schema, digest, and POA verification."""
    operation = next(
        (
            op
            for op in OPERATIONS_CATALOG
            if operation_id
            and operation_id in (op["operation_id"], op.get("id"), op.get("tool_name"))
        ),
        None,
    )
    if operation is None:
        raise ValueError("UNKNOWN_OPERATION")
    _validate_arguments({"type": "string"}, registry_digest, "registry_digest")
    _validate_arguments({"type": "string"}, request_id, "request_id")
    _validate_arguments({"type": "string"}, plan_hash, "plan_hash")
    _validate_arguments({"type": "string"}, grant_id, "grant_id")
    _validate_arguments({"type": "string"}, correlation_id, "correlation_id")
    _validate_arguments(operation["input_schema"], {} if payload is None else payload)
    if operation.get("expiresAt"):
        validate_timestamp_freshness(str(operation["expiresAt"]))
    if not operation.get("available", True):
        reason = operation.get("unavailableReason") or "operation unavailable"
        raise ValueError(f"OPERATION_UNAVAILABLE: {reason}")
    params = dict(payload) if payload is not None else {}
    current_digest = catalog_digest()
    effective_digest_arg = registry_digest or params.get("registry_digest", "")
    if effective_digest_arg and effective_digest_arg != current_digest:
        raise ValueError("CATALOG_DIGEST_MISMATCH")

    canonical_uri = operation["operation_id"]
    if canonical_uri == "fixos://diagnostics/quick":
        return run_fixos_quick()
    if canonical_uri == "fixos://diagnostics/disk":
        return run_fixos_scan_disk(path=params.get("path", "/"))
    if canonical_uri == "fixos://diagnostics/projects":
        return run_fixos_scan_projects(min_age_days=float(params.get("min_age_days", 7.0)))
    if canonical_uri == "fixos://cleanup/auto":
        return run_fixos_auto_cleanup(
            dry_run=params.get("dry_run", True),
            min_age_days=float(params.get("min_age_days", 7.0)),
            include_projects=params.get("include_projects", True),
            request_id=request_id or params.get("request_id", ""),
            registry_digest=effective_digest_arg,
            plan_hash=plan_hash or params.get("plan_hash", ""),
            grant_id=grant_id or params.get("grant_id", ""),
            correlation_id=correlation_id or params.get("correlation_id", ""),
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
    raise ValueError("OPERATION_UNAVAILABLE")


def mcp_tools_list() -> list[dict[str, Any]]:
    """Return MCP tools/list descriptor array."""
    tools: list[dict[str, Any]] = [
        {
            "name": "registry_search",
            "description": "Search FixOS MCP URI operations and return catalog digest (wellmanifest/mcp).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 50},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "task_plan",
            "description": "Map a natural-language diagnostic or cleanup request to a FixOS URI operation without executing it.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                },
                "required": ["task"],
                "additionalProperties": False,
            },
        },
        {
            "name": "task_execute",
            "description": "Execute a FixOS URI operation by operation_id with registry_digest, request_id, and POA grant.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string", "minLength": 1},
                    "payload": {"type": "object"},
                    "registry_digest": {"type": "string", "default": "", "maxLength": 64},
                    "request_id": {"type": "string", "default": "", "maxLength": 128},
                    "plan_hash": {"type": "string", "default": "", "maxLength": 64},
                    "grant_id": {"type": "string", "default": "", "maxLength": 128},
                    "correlation_id": {"type": "string", "default": "", "maxLength": 128},
                },
                "required": ["operation_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "fixos_task_status",
            "description": "Read back a durable cleanup execution receipt by request_id without repeating effects.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                },
                "required": ["request_id"],
                "additionalProperties": False,
            },
        },
    ]
    for op in OPERATIONS_CATALOG:
        if (
            not op.get("mcp_exposed", True)
            or op.get("mcp_gateway_builtin", False)
            or not op.get("available", True)
            or not op.get("tool_name")
        ):
            continue
        tools.append(
            {
                "name": op["tool_name"],
                "description": f"[{op['operation_id']}] {op['description']}",
                "annotations": op["annotations"],
                "inputSchema": op["input_schema"],
            }
        )
    return tools


def handle_mcp_tool_call(
    name: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    receipts_dir: str | Path | None = None,
    grants_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Dispatch an MCP tools/call invocation and return structured result."""
    descriptor = next((tool for tool in mcp_tools_list() if tool["name"] == name), None)
    if descriptor is None:
        raise ValueError("UNKNOWN_TOOL")
    _validate_arguments(descriptor["inputSchema"], {} if arguments is None else arguments)
    args = dict(arguments) if arguments is not None else {}
    if name == "registry_search":
        return registry_search(query=args.get("query", ""), limit=args.get("limit", 50))
    if name == "task_plan":
        return task_plan(task=args["task"])
    if name == "task_execute":
        return task_execute(
            operation_id=args["operation_id"],
            payload=args.get("payload", {}),
            registry_digest=args.get("registry_digest", ""),
            request_id=args.get("request_id", ""),
            plan_hash=args.get("plan_hash", ""),
            grant_id=args.get("grant_id", ""),
            correlation_id=args.get("correlation_id", ""),
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
    if name == "fixos_task_status":
        return task_status(args["request_id"], receipts_dir=receipts_dir)
    return task_execute(name, args, receipts_dir=receipts_dir, grants_dir=grants_dir)


def handle_jsonrpc_message(
    message: Mapping[str, Any],
    *,
    receipts_dir: str | Path | None = None,
    grants_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 MCP message and return response dict (or None for notifications)."""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), Mapping) else {}

    if msg_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "fixos-mcp", "version": __version__},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": mcp_tools_list()}}
    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        try:
            # CLI helpers print progress; stdout is reserved for JSON-RPC frames.
            with redirect_stdout(sys.stderr):
                _validate_arguments({"type": "object"}, tool_args)
                payload = handle_mcp_tool_call(
                    tool_name,
                    tool_args,
                    receipts_dir=receipts_dir,
                    grants_dir=grants_dir,
                )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                    "structuredContent": payload,
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001
            known_name = any(tool["name"] == tool_name for tool in mcp_tools_list())
            err_payload = {"error": str(exc), "tool": tool_name if known_name else ""}
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(err_payload, ensure_ascii=False)}],
                    "structuredContent": err_payload,
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve_stdio(
    *,
    receipts_dir: str | Path | None = None,
    grants_dir: str | Path | None = None,
) -> int:
    """Run the JSON-RPC 2.0 MCP server over stdin/stdout."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        if not isinstance(msg, Mapping):
            continue
        response = handle_jsonrpc_message(
            msg,
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    return serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
