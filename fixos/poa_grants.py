"""Minimal POA Profile: Typed Plans, RFC 8785 Hashing, and Bounded Single-Use Grants (#166).

Separates planning (pure/advisory) from authority issuance (`issue_poa_grant`).
MCP tools and NL plans never self-issue grants. Every mutating execution must
present a fresh `registry_digest`, matching `plan_hash`, unexpired observation,
exact target + `input_digest`, and an unconsumed single-use capability grant.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import re
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore[assignment]

POA_PLAN_SCHEMA = "wellmanifest.poa/minimal-plan/v1"
POA_GRANT_SCHEMA = "wellmanifest.authority-lifecycle/grant/v1"
CANONICALIZATION_PROFILE = "RFC8785-JCS+SHA-256"
DEFAULT_OBSERVATION_TTL_SECONDS = 300
DEFAULT_GRANT_TTL_SECONDS = 300
MAX_GRANT_TTL_SECONDS = 900

_GRANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_POA_URN_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc_iso(value: str, code: str = "INVALID_POA_TIMESTAMP") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(code)
    return parsed.astimezone(timezone.utc)


def _utf16_sort_key(key: str) -> bytes:
    """RFC 8785 Section 3.2.3 lexicographic UTF-16 code unit ordering."""
    return key.encode("utf-16-be")


def _format_jcs_float(value: float) -> str:
    """Format an IEEE-754 binary64 number per RFC 8785 Section 3.2.2.3 / ECMA-262 Number::toString."""
    from decimal import Decimal

    if not math.isfinite(value):
        raise ValueError("NON_FINITE_JSON_NUMBER")
    if value == 0.0:
        return "0"
    sign = "-" if value < 0 else ""
    abs_dec = abs(Decimal(repr(value))).normalize()
    digits_tuple = abs_dec.as_tuple()
    digits_str = "".join(str(d) for d in digits_tuple.digits).rstrip("0") or "0"
    k = len(digits_str)
    exp = abs_dec.adjusted()
    n = exp + 1
    if k <= n <= 21:
        body = digits_str + ("0" * (n - k))
    elif 0 < n < k and n <= 21:
        body = f"{digits_str[:n]}.{digits_str[n:]}"
    elif -6 < n <= 0:
        body = f"0.{'0' * (-n)}{digits_str}"
    else:
        mantissa = digits_str[0] if k == 1 else f"{digits_str[0]}.{digits_str[1:]}"
        exp_sign = "+" if exp >= 0 else "-"
        body = f"{mantissa}e{exp_sign}{abs(exp)}"
    return f"{sign}{body}"


def _jcs_serialize(value: Any) -> str:
    """Serialize JSON value under pinned RFC 8785 (JCS) subset, rejecting non-finite numbers."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is int:
        return str(value)
    if type(value) is float:
        return _format_jcs_float(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs_serialize(item) for item in value) + "]"
    if isinstance(value, Mapping):
        for k in value:
            if not isinstance(k, str):
                raise TypeError("NON_STRING_JSON_KEY")
        ordered_keys = sorted(value.keys(), key=_utf16_sort_key)
        members = [f"{_jcs_serialize(k)}:{_jcs_serialize(value[k])}" for k in ordered_keys]
        return "{" + ",".join(members) + "}"
    raise TypeError(f"UNSUPPORTED_CANONICAL_TYPE: {type(value).__name__}")


def jcs_canonical_bytes(value: Any) -> bytes:
    return _jcs_serialize(value).encode("utf-8")


def jcs_sha256(value: Any) -> str:
    return hashlib.sha256(jcs_canonical_bytes(value)).hexdigest()


def cleanup_poa_input(
    *,
    dry_run: bool,
    min_age_days: float,
    include_projects: bool,
) -> dict[str, Any]:
    """Return canonical input payload bound by POA plans and idempotency digests."""
    return {
        "dry_run": bool(dry_run),
        "min_age_days": float(min_age_days),
        "include_projects": bool(include_projects),
    }


def cleanup_poa_target(
    *,
    include_projects: bool,
    min_age_days: float,
    root: str = "/",
) -> dict[str, Any]:
    """Return canonical target descriptor for fixos://cleanup/auto."""
    categories = ["safe_user_caches", "additional_caches", "build_caches"]
    if include_projects:
        categories.extend(["project_artifacts", "state_partitions"])
    return {
        "host": "local",
        "root": root,
        "include_projects": bool(include_projects),
        "min_age_days": float(min_age_days),
        "categories": categories,
    }


def grants_dir(custom_dir: str | Path | None = None) -> Path:
    if custom_dir:
        base = Path(custom_dir)
    else:
        env_dir = os.environ.get("FIXOS_POA_GRANTS_DIR")
        base = Path(env_dir) if env_dir else Path.home() / ".local" / "state" / "fixos" / "poa-grants"
    base.mkdir(parents=True, exist_ok=True)
    return base


def compile_poa_plan(
    *,
    operation_id: str,
    registry_digest: str,
    normalized_input: Mapping[str, Any],
    target: Mapping[str, Any],
    effects: list[str],
    observation: Mapping[str, Any] | None = None,
    observation_ttl_seconds: int = DEFAULT_OBSERVATION_TTL_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a closed, typed POA plan with deterministic RFC 8785 plan_hash (grants_authority=False)."""
    if not _SHA256_RE.fullmatch(registry_digest or ""):
        raise ValueError("INVALID_REGISTRY_DIGEST")
    if not (1 <= int(observation_ttl_seconds) <= MAX_GRANT_TTL_SECONDS):
        raise ValueError("INVALID_OBSERVATION_TTL")
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    observed_at = _utc_iso(ref_now)
    valid_until = _utc_iso(ref_now + timedelta(seconds=int(observation_ttl_seconds)))
    input_digest = jcs_sha256(normalized_input)
    target_digest = jcs_sha256(target)

    plan_seed = f"{operation_id}:{registry_digest}:{input_digest}:{target_digest}:{observed_at}"
    plan_uuid = uuid.uuid5(
        _POA_URN_NAMESPACE,
        f"https://wellmanifest.org/semcod/fixos/poa-plan/{plan_seed}",
    )
    plan_urn = f"urn:uuid:{plan_uuid}"

    body: dict[str, Any] = {
        "schema": POA_PLAN_SCHEMA,
        "plan_id": f"plan-{plan_uuid.hex[:16]}",
        "plan_urn": plan_urn,
        "closed_task": True,
        "grants_authority": False,
        "executable": False,
        "operation_id": operation_id,
        "registry_digest": registry_digest,
        "canonicalization_profile": CANONICALIZATION_PROFILE,
        "input_artifact": {
            "digest": input_digest,
            "normalized": dict(normalized_input),
        },
        "target": dict(target),
        "target_digest": target_digest,
        "observation": {
            "observed_at": observed_at,
            "valid_until": valid_until,
            "ttl_seconds": int(observation_ttl_seconds),
            "summary": dict(observation or {}),
        },
        "effects": list(effects),
        "readback_contract": {
            "required_for_succeeded": True,
            "states": ["succeeded", "partial", "failed", "uncertain"],
        },
    }
    plan_hash = jcs_sha256(body)
    return {**body, "plan_hash": plan_hash}


def plan_cleanup_poa(
    *,
    registry_digest: str,
    min_age_days: float = 7.0,
    include_projects: bool = True,
    observation: Mapping[str, Any] | None = None,
    observation_ttl_seconds: int = DEFAULT_OBSERVATION_TTL_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compile a minimal POA plan for mutating fixos://cleanup/auto (`dry_run=False`)."""
    norm_in = cleanup_poa_input(
        dry_run=False,
        min_age_days=min_age_days,
        include_projects=include_projects,
    )
    target = cleanup_poa_target(include_projects=include_projects, min_age_days=min_age_days)
    return compile_poa_plan(
        operation_id="fixos://cleanup/auto",
        registry_digest=registry_digest,
        normalized_input=norm_in,
        target=target,
        effects=["local_write"],
        observation=observation,
        observation_ttl_seconds=observation_ttl_seconds,
        now=now,
    )


def verify_poa_plan(
    plan: Mapping[str, Any],
    *,
    expected_operation_id: str,
    expected_registry_digest: str,
    expected_input_digest: str,
    expected_target_digest: str,
    now: datetime | None = None,
) -> None:
    """Verify plan schema, canonical RFC 8785 hash, observation freshness, and exact bindings."""
    if plan.get("schema") != POA_PLAN_SCHEMA or plan.get("closed_task") is not True:
        raise ValueError("INVALID_POA_PLAN")
    if plan.get("canonicalization_profile") != CANONICALIZATION_PROFILE:
        raise ValueError("UNSUPPORTED_CANONICALIZATION_PROFILE")
    if plan.get("grants_authority") is not False:
        raise ValueError("POA_PLAN_MUST_NOT_GRANT_AUTHORITY")
    body = {k: v for k, v in plan.items() if k != "plan_hash"}
    if jcs_sha256(body) != plan.get("plan_hash"):
        raise ValueError("POA_PLAN_HASH_MISMATCH")

    if plan.get("operation_id") != expected_operation_id:
        raise ValueError("POA_OPERATION_MISMATCH")
    if plan.get("registry_digest") != expected_registry_digest:
        raise ValueError("CATALOG_DIGEST_MISMATCH")
    input_art = plan.get("input_artifact")
    if not isinstance(input_art, Mapping) or input_art.get("digest") != expected_input_digest:
        raise ValueError("POA_INPUT_DRIFT")
    if plan.get("target_digest") != expected_target_digest:
        raise ValueError("POA_TARGET_DRIFT")

    obs = plan.get("observation")
    if obs is None or not hasattr(obs, "get"):
        raise ValueError("MISSING_POA_OBSERVATION")
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if _parse_utc_iso(str(obs.get("valid_until", "")), "POA_OBSERVATION_EXPIRED") <= ref_now:
        raise ValueError("POA_OBSERVATION_EXPIRED")


def _atomic_write(path: Path, data: Mapping[str, Any]) -> None:
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    if os.name != "nt":
        with contextlib.suppress(OSError):
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)


def issue_poa_grant(
    plan: Mapping[str, Any],
    *,
    issuer: str = "controller:local-policy",
    subject: str = "mcp:fixos-server",
    ttl_seconds: int = DEFAULT_GRANT_TTL_SECONDS,
    store_dir: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Separate policy/controller operation issuing a bounded single-use grant bound to plan_hash."""
    if not issuer.strip() or issuer.startswith(("mcp:", "nl:", "tool:")):
        raise ValueError("SELF_ISSUED_GRANT_FORBIDDEN")
    if not (1 <= int(ttl_seconds) <= MAX_GRANT_TTL_SECONDS):
        raise ValueError("INVALID_POA_GRANT_TTL")

    body = {k: v for k, v in plan.items() if k != "plan_hash"}
    plan_hash = plan.get("plan_hash")
    if not isinstance(plan_hash, str) or jcs_sha256(body) != plan_hash:
        raise ValueError("POA_PLAN_HASH_MISMATCH")

    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    obs = plan.get("observation") if isinstance(plan.get("observation"), Mapping) else {}
    obs_until = _parse_utc_iso(str(obs.get("valid_until", "")), "POA_OBSERVATION_EXPIRED")
    if obs_until <= ref_now:
        raise ValueError("POA_OBSERVATION_EXPIRED")

    grant_expires = min(obs_until, ref_now + timedelta(seconds=int(ttl_seconds)))
    grant_id = f"grant-{uuid.uuid4().hex[:16]}"
    grant_uuid = uuid.uuid5(
        _POA_URN_NAMESPACE,
        f"https://wellmanifest.org/semcod/fixos/poa-grant/{grant_id}",
    )
    input_art = plan.get("input_artifact") if isinstance(plan.get("input_artifact"), Mapping) else {}

    grant_body: dict[str, Any] = {
        "schema": POA_GRANT_SCHEMA,
        "grantId": grant_id,
        "grant_urn": f"urn:uuid:{grant_uuid}",
        "issuer": issuer,
        "subject": subject,
        "status": "active",
        "single_use": True,
        "issuedAt": _utc_iso(ref_now),
        "expiresAt": _utc_iso(grant_expires),
        "scope": [str(plan["operation_id"])],
        "operation_id": str(plan["operation_id"]),
        "registry_digest": str(plan["registry_digest"]),
        "plan_hash": plan_hash,
        "input_digest": str(input_art.get("digest", "")),
        "target_digest": str(plan.get("target_digest", "")),
        "canonicalization_profile": CANONICALIZATION_PROFILE,
    }
    grant_doc = {**grant_body, "grant_digest": jcs_sha256(grant_body)}

    base = grants_dir(store_dir)
    _atomic_write(base / f"{grant_id}.json", grant_doc)
    plan_path = base / f"plan-{plan_hash}.json"
    if not plan_path.exists():
        _atomic_write(plan_path, dict(plan))

    return grant_doc


def verify_and_consume_poa_grant(
    *,
    grant_id: str,
    plan_hash: str,
    operation_id: str,
    caller_registry_digest: str,
    current_registry_digest: str,
    normalized_input: Mapping[str, Any],
    target: Mapping[str, Any],
    store_dir: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fail-closed verifier consuming a single-use POA grant before any mutating execution."""
    if not caller_registry_digest:
        raise ValueError("MISSING_REGISTRY_DIGEST")
    if caller_registry_digest != current_registry_digest:
        raise ValueError("CATALOG_DIGEST_MISMATCH")
    if not plan_hash:
        raise ValueError("MISSING_POA_PLAN_HASH")
    if not _SHA256_RE.fullmatch(plan_hash):
        raise ValueError("POA_PLAN_HASH_MISMATCH")
    clean_gid = (grant_id or "").strip()
    if not clean_gid:
        raise ValueError("MISSING_POA_GRANT")
    if not _GRANT_ID_RE.fullmatch(clean_gid) or ".." in clean_gid:
        raise ValueError("INVALID_POA_GRANT")

    base = grants_dir(store_dir)
    gpath = base / f"{clean_gid}.json"
    consumed_path = base / f"{clean_gid}.consumed"
    lock_path = base / f"{clean_gid}.lock"
    plan_path = base / f"plan-{plan_hash}.json"

    if not gpath.is_file():
        raise ValueError("UNKNOWN_POA_GRANT")

    input_digest = jcs_sha256(normalized_input)
    target_digest = jcs_sha256(target)
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    os_locked = False
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os_locked = True
        elif msvcrt is not None:  # pragma: no cover - Windows
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            os_locked = True
        if consumed_path.exists():
            raise ValueError("POA_GRANT_REPLAYED")

        grant_doc = json.loads(gpath.read_text(encoding="utf-8"))
        grant_body = {k: v for k, v in grant_doc.items() if k != "grant_digest"}
        if jcs_sha256(grant_body) != grant_doc.get("grant_digest"):
            raise ValueError("CORRUPTED_POA_GRANT")

        if grant_doc.get("status") != "active":
            raise ValueError("INACTIVE_POA_GRANT")
        if _parse_utc_iso(str(grant_doc.get("expiresAt", "")), "POA_GRANT_EXPIRED") <= ref_now:
            raise ValueError("POA_GRANT_EXPIRED")

        if grant_doc.get("registry_digest") != current_registry_digest:
            raise ValueError("CATALOG_DIGEST_MISMATCH")
        if grant_doc.get("plan_hash") != plan_hash:
            raise ValueError("POA_PLAN_HASH_MISMATCH")
        if grant_doc.get("operation_id") != operation_id or operation_id not in grant_doc.get("scope", []):
            raise ValueError("POA_SCOPE_MISMATCH")
        if grant_doc.get("input_digest") != input_digest:
            raise ValueError("POA_INPUT_DRIFT")
        if grant_doc.get("target_digest") != target_digest:
            raise ValueError("POA_TARGET_DRIFT")

        if not plan_path.is_file():
            raise ValueError("MISSING_POA_PLAN_ARTIFACT")
        plan_doc = json.loads(plan_path.read_text(encoding="utf-8"))
        verify_poa_plan(
            plan_doc,
            expected_operation_id=operation_id,
            expected_registry_digest=current_registry_digest,
            expected_input_digest=input_digest,
            expected_target_digest=target_digest,
            now=ref_now,
        )

        _atomic_write(
            consumed_path,
            {
                "grantId": clean_gid,
                "consumedAt": _utc_iso(ref_now),
                "plan_hash": plan_hash,
                "operation_id": operation_id,
            },
        )
        return {
            "grantId": clean_gid,
            "grant_urn": grant_doc["grant_urn"],
            "issuer": grant_doc["issuer"],
            "plan_hash": plan_hash,
        }
    finally:
        if os_locked:
            with contextlib.suppress(OSError):
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                elif msvcrt is not None:  # pragma: no cover - Windows
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        with contextlib.suppress(OSError):
            os.close(fd)
