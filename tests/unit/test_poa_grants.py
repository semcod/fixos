"""Unit tests for minimal POA plans, RFC 8785 JCS hashing, and bounded single-use grants (#166)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fixos.mcp_server import (
    catalog_digest,
    handle_mcp_tool_call,
    task_execute,
    task_plan,
)
from fixos.poa_grants import (
    CANONICALIZATION_PROFILE,
    issue_poa_grant,
    jcs_canonical_bytes,
    jcs_sha256,
    plan_cleanup_poa,
)


def test_rfc8785_utf16_key_order_and_non_finite_rejection():
    # U+E000 (BMP, single UTF-16 unit 0xE000) vs U+10000 (supplementary, surrogate pair 0xD800 0xDC00):
    # Python sort_keys=True sorts by Unicode code point (\ue000 before \U00010000),
    # whereas RFC 8785 Section 3.2.3 sorts by UTF-16 code units (\U00010000 [0xD800] before \ue000 [0xE000]).
    obj = {"\ue000": 1, "\U00010000": 2}
    canonical_str = jcs_canonical_bytes(obj).decode("utf-8")
    assert canonical_str.index("\U00010000") < canonical_str.index("\ue000")

    # -0.0, integer-valued float, and ECMA-262 / RFC 8785 exponent boundary vectors
    assert jcs_canonical_bytes({"n": -0.0, "days": 7.0}) == b'{"days":7,"n":0}'
    assert jcs_canonical_bytes({"a": 1e-6, "b": 1e-7}) == b'{"a":0.000001,"b":1e-7}'
    assert jcs_canonical_bytes({"c": 1e20, "d": 1e21}) == (
        b'{"c":100000000000000000000,"d":1e+21}'
    )

    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="NON_FINITE_JSON_NUMBER"):
            jcs_sha256({"bad": bad})


def test_nl_plan_and_self_issuance_never_grant_authority(tmp_path: Path):
    nl_plan = task_plan("zwolnij miejsce na dysku automatycznie")
    assert nl_plan["grants_authority"] is False
    assert nl_plan["executable"] is False

    poa_plan = plan_cleanup_poa(registry_digest=catalog_digest(), include_projects=False)
    assert poa_plan["canonicalization_profile"] == CANONICALIZATION_PROFILE
    assert poa_plan["grants_authority"] is False
    assert poa_plan["executable"] is False
    assert poa_plan["plan_urn"].startswith("urn:uuid:")

    for forbidden_issuer in ("mcp:fixos", "nl:router", "tool:fixos_auto_cleanup", "  "):
        with pytest.raises(ValueError, match="SELF_ISSUED_GRANT_FORBIDDEN"):
            issue_poa_grant(poa_plan, issuer=forbidden_issuer, store_dir=tmp_path)


def test_mutating_cleanup_rejects_missing_expired_replayed_and_drifted_grants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("fixos.mcp_server.scan_user_cache_dirs", list)
    monkeypatch.setattr("fixos.mcp_server.scan_additional_safe_caches", list)
    monkeypatch.setattr("fixos.mcp_server.scan_build_and_package_caches", list)
    receipts_dir = tmp_path / "receipts"
    grants_dir = tmp_path / "grants"
    digest = catalog_digest()

    # 1. Direct fixos_auto_cleanup tool call with dry_run=False cannot bypass registry_digest or grant
    with pytest.raises(ValueError, match="MISSING_REGISTRY_DIGEST"):
        handle_mcp_tool_call(
            "fixos_auto_cleanup",
            {"dry_run": False, "include_projects": False, "request_id": "no-digest"},
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    with pytest.raises(ValueError, match="MISSING_POA_PLAN_HASH"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "include_projects": False},
            registry_digest=digest,
            request_id="no-plan",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    plan = plan_cleanup_poa(registry_digest=digest, min_age_days=7.0, include_projects=False)
    with pytest.raises(ValueError, match="MISSING_POA_GRANT"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "include_projects": False},
            registry_digest=digest,
            plan_hash=plan["plan_hash"],
            request_id="no-grant",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    # 2. Expired grant rejected
    t0 = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)
    old_plan = plan_cleanup_poa(
        registry_digest=digest,
        min_age_days=7.0,
        include_projects=False,
        now=t0 - timedelta(minutes=20),
        observation_ttl_seconds=600,
    )
    with pytest.raises(ValueError, match="POA_OBSERVATION_EXPIRED"):
        issue_poa_grant(old_plan, store_dir=grants_dir, now=t0)

    short_plan = plan_cleanup_poa(
        registry_digest=digest,
        min_age_days=7.0,
        include_projects=False,
        now=datetime.now(timezone.utc) - timedelta(seconds=10),
        observation_ttl_seconds=300,
    )
    expired_grant = issue_poa_grant(
        short_plan,
        ttl_seconds=5,
        store_dir=grants_dir,
        now=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    with pytest.raises(ValueError, match="POA_GRANT_EXPIRED"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "include_projects": False},
            registry_digest=digest,
            plan_hash=short_plan["plan_hash"],
            grant_id=expired_grant["grantId"],
            request_id="expired-grant-req",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    # 3. Input/target drift rejected without consuming the valid grant for its legitimate target
    valid_plan = plan_cleanup_poa(registry_digest=digest, min_age_days=7.0, include_projects=False)
    valid_grant = issue_poa_grant(valid_plan, store_dir=grants_dir)

    with pytest.raises(ValueError, match="POA_INPUT_DRIFT"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "min_age_days": 14.0, "include_projects": False},
            registry_digest=digest,
            plan_hash=valid_plan["plan_hash"],
            grant_id=valid_grant["grantId"],
            request_id="drifted-input-req",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    with pytest.raises(ValueError, match="POA_INPUT_DRIFT"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "min_age_days": 7.0, "include_projects": True},
            registry_digest=digest,
            plan_hash=valid_plan["plan_hash"],
            grant_id=valid_grant["grantId"],
            request_id="drifted-target-req",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )

    # 4. Legitimate single-use execution succeeds, and replaying the grant on a second request_id fails closed
    ok = task_execute(
        "fixos://cleanup/auto",
        {"dry_run": False, "min_age_days": 7.0, "include_projects": False},
        registry_digest=digest,
        plan_hash=valid_plan["plan_hash"],
        grant_id=valid_grant["grantId"],
        request_id="legit-exec-1",
        receipts_dir=receipts_dir,
        grants_dir=grants_dir,
    )
    assert ok["state"] == "succeeded"
    assert ok["authorization"]["grantId"] == valid_grant["grantId"]

    with pytest.raises(ValueError, match="POA_GRANT_REPLAYED"):
        task_execute(
            "fixos://cleanup/auto",
            {"dry_run": False, "min_age_days": 7.0, "include_projects": False},
            registry_digest=digest,
            plan_hash=valid_plan["plan_hash"],
            grant_id=valid_grant["grantId"],
            request_id="replay-attempt-2",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
