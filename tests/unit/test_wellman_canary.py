"""End-to-end conformance & runtime canary tests for POA, MCP, and NL-URI adoption (#168)."""

from __future__ import annotations

from pathlib import Path

from fixos.poa_canary import (
    CANARY_REPORT_SCHEMA,
    run_conformance_and_runtime_canary,
)


def test_conformance_and_runtime_canary_separates_manifest_from_runtime_evidence():
    repo_root = Path(__file__).resolve().parents[2]
    report = run_conformance_and_runtime_canary(repo_root)
    assert report["schema"] == CANARY_REPORT_SCHEMA

    # Manifest declaration alone never proves S5 runtime execution
    assert report["declared_adoption"]["proves_runtime_s5"] is False

    # Static checkers pass independently
    assert report["static_checkers"]["passed"] is True
    assert report["static_checkers"]["fastmcp_hygiene"]["passed"] is True
    assert report["static_checkers"]["registry_v1_operation_count"] > 20

    # Observed runtime canary executes handshake, URN reads, NL negative guards, and POA gates
    obs = report["observed_runtime_canary"]
    assert obs["passed"] is True
    assert obs["handshake_verified"] is True
    assert obs["nl_negative_guards_verified"] is True
    assert obs["poa_ungranted_mutation_blocked"] is True
    assert obs["urn_resources_verified"] == 4
    assert obs["idempotency_conflict_verified"] is True
