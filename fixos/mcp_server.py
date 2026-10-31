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
import os
import re
import sys
import uuid
from collections.abc import Mapping
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fixos import __version__

CATALOG_SCHEMA = "wellmanifest.mcp/operation-catalog/v1"
RECEIPT_SCHEMA = "wellmanifest.mcp/task-receipt/v1"
PLAN_SCHEMA = "wellmanifest.nl-dsl-llm/task-plan/v1"
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

OPERATIONS_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "operation_id": "fixos://diagnostics/quick",
        "tool_name": "fixos_quick",
        "title": "Quick deterministic system & storage snapshot",
        "description": "Collect fast local CPU, RAM, disk, safe cache, and top process telemetry without LLM calls.",
        "effect": "read",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "operation_id": "fixos://diagnostics/disk",
        "tool_name": "fixos_scan_disk",
        "title": "Disk usage & safe cache inventory",
        "description": "Analyze root filesystem free space, safe user caches, and JetBrains/build cache candidates.",
        "effect": "read",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "/"},
            },
            "additionalProperties": False,
        },
    },
    {
        "operation_id": "fixos://diagnostics/projects",
        "tool_name": "fixos_scan_projects",
        "title": "Scan stale developer project artifacts & state partitions",
        "description": "Discover unused developer build/venv artifacts and date-partitioned app state older than min_age_days.",
        "effect": "read",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "min_age_days": {"type": "number", "default": 7.0},
            },
            "additionalProperties": False,
        },
    },
    {
        "operation_id": "fixos://cleanup/auto",
        "tool_name": "fixos_auto_cleanup",
        "title": "Deterministic safe disk cleanup",
        "description": "Reclaim disk space from safe caches, stale (>7d) unused project artifacts, and date-partitioned state.",
        "effect": "mutate",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "default": True},
                "min_age_days": {"type": "number", "default": 7.0},
                "include_projects": {"type": "boolean", "default": True},
                "request_id": {
                    "type": "string",
                    "default": "",
                    "maxLength": 128,
                    "description": "Opaque ID starting with a letter/digit, using letters, digits, dots, underscores or hyphens; no '..'. Empty generates an ID.",
                },
            },
            "additionalProperties": False,
        },
    },
)


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def catalog_digest() -> str:
    """Return deterministic SHA-256 digest of the registered MCP operations."""
    return _canonical_digest(list(OPERATIONS_CATALOG))


def _receipts_dir(custom_dir: str | Path | None = None) -> Path:
    if custom_dir:
        base = Path(custom_dir)
    else:
        env_dir = os.environ.get("FIXOS_MCP_RECEIPTS_DIR")
        base = Path(env_dir) if env_dir else Path.home() / ".local" / "state" / "fixos" / "mcp-receipts"
    base.mkdir(parents=True, exist_ok=True)
    return base


def registry_search(query: str = "", limit: int = 12) -> dict[str, Any]:
    """Search registered FixOS MCP URI operations (wellmanifest/mcp discovery)."""
    q = (query or "").strip().lower()
    bounded_limit = max(1, min(int(limit), 50))
    matches: list[dict[str, Any]] = []
    for op in OPERATIONS_CATALOG:
        haystack = f"{op['operation_id']} {op['tool_name']} {op['title']} {op['description']}".lower()
        if not q or q in haystack or any(tok in haystack for tok in q.split()):
            matches.append(dict(op))
        if len(matches) >= bounded_limit:
            break
    return {
        "schema": CATALOG_SCHEMA,
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
    clean_id = (request_id or "").strip()
    if not _REQUEST_ID_RE.fullmatch(clean_id) or ".." in clean_id:
        raise ValueError("invalid_request_id")
    return clean_id


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
    rpath = _receipts_dir(receipts_dir) / f"{clean_id}.json"
    if not rpath.is_file():
        return {
            "schema": RECEIPT_SCHEMA,
            "found": False,
            "request_id": clean_id,
        }
    data = json.loads(rpath.read_text(encoding="utf-8"))
    return {**data, "found": True, "replayed": True}


def run_fixos_auto_cleanup(
    *,
    dry_run: bool = True,
    min_age_days: float = 7.0,
    include_projects: bool = True,
    request_id: str = "",
    receipts_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute bounded deterministic cleanup or dry-run preview with durable receipt persistence."""
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
    existing = task_status(req_id, receipts_dir=receipts_dir)
    if existing.get("found"):
        return existing

    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    before_free = shutil.disk_usage("/").free

    user_caches = [c for c in scan_user_cache_dirs() if c.get("safe")]
    add_caches = scan_additional_safe_caches()
    build_caches = scan_build_and_package_caches()
    proj_items = scan_unused_recent_project_artifacts(min_age_days=float(min_age_days)) if include_projects else []
    part_items = scan_stale_app_state_partitions(min_age_days=float(min_age_days)) if include_projects else []

    planned_bytes = (
        sum(int(c.get("size_bytes", 0)) for c in user_caches)
        + sum(int(c.get("size_bytes", 0)) for c in add_caches)
        + sum(int(c.get("size_bytes", 0)) for c in build_caches)
        + sum(int(c.get("size_bytes", 0)) for c in proj_items)
        + sum(int(c.get("size_bytes", 0)) for c in part_items)
    )

    actions_taken: list[str] = []
    days_int = max(1, int(min_age_days))
    if not dry_run:
        if user_caches:
            _cleanup_user_cache(json_output=False, dry_run=False, list_only=False, yes=True)
            actions_taken.append(f"user_caches:{len(user_caches)}")
        if add_caches:
            cleanup_additional_caches(dry_run=False, yes=True)
            actions_taken.append(f"additional_caches:{len(add_caches)}")
        if build_caches:
            _cleanup_build_caches(
                json_output=False,
                dry_run=False,
                list_only=False,
                yes=True,
                include_build_cache=True,
                clean_state_old=False,
                clean_projects_old=False,
            )
            actions_taken.append(f"build_caches:{len(build_caches)}")
        if proj_items:
            _cleanup_projects_old(
                json_output=False,
                dry_run=False,
                list_only=False,
                yes=True,
                days=days_int,
            )
            actions_taken.append(f"project_artifacts:{len(proj_items)}")
        if part_items:
            _cleanup_state_old(
                json_output=False,
                dry_run=False,
                list_only=False,
                yes=True,
                days=days_int,
            )
            actions_taken.append(f"state_partitions:{len(part_items)}")

    after_free = shutil.disk_usage("/").free
    reclaimed_bytes = max(0, after_free - before_free) if not dry_run else 0
    completed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "request_id": req_id,
        "operation_id": "fixos://cleanup/auto",
        "effect": "read" if dry_run else "mutate",
        "dry_run": bool(dry_run),
        "state": "planned" if dry_run else "succeeded",
        "started_at": started_at,
        "completed_at": completed_at,
        "registry_digest": catalog_digest(),
        "planned_reclaimable_bytes": planned_bytes,
        "reclaimed_bytes": reclaimed_bytes,
        "free_bytes_before": before_free,
        "free_bytes_after": after_free,
        "actions": actions_taken,
        "counts": {
            "safe_user_caches": len(user_caches),
            "additional_caches": len(add_caches),
            "build_caches": len(build_caches),
            "project_artifacts": len(proj_items),
            "state_partitions": len(part_items),
        },
    }
    receipt["receipt_hash"] = _canonical_digest(receipt)
    rpath = _receipts_dir(receipts_dir) / f"{req_id}.json"
    rpath.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {**receipt, "found": True, "replayed": False}


def task_execute(
    operation_id: str,
    payload: Mapping[str, Any] | None = None,
    *,
    registry_digest: str = "",
    request_id: str = "",
    receipts_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Execute a registered FixOS URI operation with optional digest verification."""
    params = dict(payload or {})
    current_digest = catalog_digest()
    if registry_digest and registry_digest != current_digest:
        raise ValueError(f"CATALOG_DIGEST_MISMATCH: expected {registry_digest}, actual {current_digest}")

    if operation_id in ("fixos://diagnostics/quick", "fixos_quick"):
        return run_fixos_quick()
    if operation_id in ("fixos://diagnostics/disk", "fixos_scan_disk"):
        return run_fixos_scan_disk(path=str(params.get("path", "/")))
    if operation_id in ("fixos://diagnostics/projects", "fixos_scan_projects"):
        return run_fixos_scan_projects(min_age_days=float(params.get("min_age_days", 7.0)))
    if operation_id in ("fixos://cleanup/auto", "fixos_auto_cleanup"):
        return run_fixos_auto_cleanup(
            dry_run=bool(params.get("dry_run", True)),
            min_age_days=float(params.get("min_age_days", 7.0)),
            include_projects=bool(params.get("include_projects", True)),
            request_id=str(request_id or params.get("request_id", "")),
            receipts_dir=receipts_dir,
        )
    raise ValueError(f"UNKNOWN_OPERATION: {operation_id}")


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
                    "limit": {"type": "integer", "default": 12},
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
            "description": "Execute a FixOS URI operation by operation_id with optional registry_digest and request_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string"},
                    "payload": {"type": "object"},
                    "registry_digest": {"type": "string", "default": ""},
                    "request_id": {"type": "string", "default": ""},
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
) -> dict[str, Any]:
    """Dispatch an MCP tools/call invocation and return structured result."""
    args = dict(arguments or {})
    if name == "registry_search":
        return registry_search(query=str(args.get("query", "")), limit=int(args.get("limit", 12)))
    if name == "task_plan":
        return task_plan(task=str(args.get("task", "")))
    if name == "task_execute":
        return task_execute(
            operation_id=str(args.get("operation_id", "")),
            payload=args.get("payload") if isinstance(args.get("payload"), Mapping) else {},
            registry_digest=str(args.get("registry_digest", "")),
            request_id=str(args.get("request_id", "")),
            receipts_dir=receipts_dir,
        )
    if name == "fixos_task_status":
        return task_status(str(args.get("request_id", "")), receipts_dir=receipts_dir)
    return task_execute(name, args, receipts_dir=receipts_dir)


def handle_jsonrpc_message(
    message: Mapping[str, Any],
    *,
    receipts_dir: str | Path | None = None,
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
        tool_name = str(params.get("name", ""))
        tool_args = params.get("arguments") if isinstance(params.get("arguments"), Mapping) else {}
        try:
            # CLI helpers print progress; stdout is reserved for JSON-RPC frames.
            with redirect_stdout(sys.stderr):
                payload = handle_mcp_tool_call(tool_name, tool_args, receipts_dir=receipts_dir)
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
            err_payload = {"error": str(exc), "tool": tool_name}
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


def serve_stdio(*, receipts_dir: str | Path | None = None) -> int:
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
        response = handle_jsonrpc_message(msg, receipts_dir=receipts_dir)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    return serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
