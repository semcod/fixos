"""End-to-End POA, MCP, and NL-URI Conformance & Runtime Canary (#168).

Reports declared adoption levels, deterministic static contract checks, and
observed runtime canary execution separately (`proves_runtime_s5=False` on
static manifest declarations). Safe to execute in CI without touching user data.
"""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path
from typing import Any

from fixos.mcp_receipts import verify_receipt_integrity
from fixos.mcp_resources import CATALOG_RESOURCE_URN, QUICK_SNAPSHOT_RESOURCE_URN
from fixos.mcp_server import (
    catalog_digest,
    handle_jsonrpc_message,
    task_execute,
    task_plan,
)
from fixos.poa_grants import issue_poa_grant, plan_cleanup_poa
from fixos.poa_registry import export_mcp_registry_v1, verify_capability_parity

CANARY_REPORT_SCHEMA = "wellmanifest.fixos/runtime-canary-report/v1"


def inspect_declared_requirements(repo_root: Path) -> dict[str, Any]:
    """Read declared standard requirements and adoption manifest without claiming runtime proof."""
    req_path = repo_root / ".governance" / "standard-requirements.json"
    adopt_path = repo_root / ".governance" / "standard-adoption.json"
    requirements: dict[str, str] = {}
    if req_path.is_file():
        doc = json.loads(req_path.read_text(encoding="utf-8"))
        for item in doc.get("requirements", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                requirements[item["id"]] = str(item.get("minimumLevel", ""))
    adopted: dict[str, str] = {}
    if adopt_path.is_file():
        adoc = json.loads(adopt_path.read_text(encoding="utf-8"))
        for item in adoc.get("adoptions", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                adopted[item["id"]] = str(item.get("level", ""))
    return {
        "requirements": requirements,
        "adopted_levels": adopted,
        "proves_runtime_s5": False,
    }


def verify_no_unsupported_fastmcp_declarations(repo_root: Path) -> dict[str, Any]:
    """Ensure source AST and pyproject.toml do not claim or import undeclared FastMCP dependencies."""
    pyproject = repo_root / "pyproject.toml"
    pyproject_text = pyproject.read_text(encoding="utf-8").lower() if pyproject.is_file() else ""
    if "fastmcp" in pyproject_text:
        raise ValueError("UNSUPPORTED_FASTMCP_DEPENDENCY_DECLARATION")

    pkg_dir = repo_root / "fixos"
    checked_files = 0
    for py_file in sorted(pkg_dir.rglob("*.py")):
        if py_file.name == "poa_canary.py":
            continue
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        checked_files += 1
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name.split(".")[0] == "fastmcp" for alias in node.names
            ):
                raise ValueError(f"UNDECLARED_FASTMCP_IMPORT: {py_file.name}")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".")[0] == "fastmcp"
            ):
                raise ValueError(f"UNDECLARED_FASTMCP_IMPORT: {py_file.name}")
        doc = ast.get_docstring(tree) or ""
        if "fastmcp" in doc.lower():
            raise ValueError(f"UNSUPPORTED_FASTMCP_DOCSTRING_CLAIM: {py_file.name}")

    return {"passed": True, "checked_source_files": checked_files}


def run_observed_runtime_canary() -> dict[str, Any]:
    """Execute live isolated MCP + URN resources + NL-URI + POA single-use grant canary."""
    with tempfile.TemporaryDirectory(prefix="fixos-poa-canary-") as tmp:
        base = Path(tmp)
        receipts_dir = base / "receipts"
        grants_dir = base / "grants"

        # 1. MCP handshake + capabilities
        init = handle_jsonrpc_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
        assert init is not None
        caps = init["result"]["capabilities"]
        if "tools" not in caps or "resources" not in caps:
            raise RuntimeError("CANARY_HANDSHAKE_MISSING_CAPABILITIES")

        # 2. NL-URI positive + negative (negation, standalone auto, unknown)
        pos_plan = task_plan("Wyczyść bezpieczny cache na dysku")
        neg_plan = task_plan("nie usuwaj nic automatycznie")
        auto_plan = task_plan("auto")
        unk_plan = task_plan("opowiedz bajkę o smoku")
        if (
            pos_plan["status"] != "ok"
            or pos_plan["grants_authority"] is not False
            or neg_plan["status"] != "clarify"
            or auto_plan["status"] != "clarify"
            or unk_plan["status"] != "unsupported"
        ):
            raise RuntimeError("CANARY_NL_ROUTER_INVARIANT_FAILED")

        # 3. Negative POA mutation gate (missing grant rejected)
        digest = catalog_digest()
        rejected_ungranted = False
        try:
            task_execute(
                "fixos://cleanup/auto",
                {"dry_run": False, "include_projects": False},
                registry_digest=digest,
                request_id="canary-ungranted",
                receipts_dir=receipts_dir,
                grants_dir=grants_dir,
            )
        except ValueError as exc:
            rejected_ungranted = "MISSING_POA" in str(exc)
        if not rejected_ungranted:
            raise RuntimeError("CANARY_UNGRANTED_MUTATION_NOT_BLOCKED")

        # 4. Dry-run preview receipt + POA plan + URN resources read-back
        dry_receipt = task_execute(
            "fixos://cleanup/auto",
            {"dry_run": True, "include_projects": False},
            registry_digest=digest,
            request_id="canary-preview-1",
            receipts_dir=receipts_dir,
            grants_dir=grants_dir,
        )
        if not verify_receipt_integrity(dry_receipt):
            raise RuntimeError("CANARY_RECEIPT_INTEGRITY_FAILED")

        poa_plan = plan_cleanup_poa(registry_digest=digest, include_projects=False)
        grant = issue_poa_grant(poa_plan, store_dir=grants_dir)

        for urn in (
            CATALOG_RESOURCE_URN,
            QUICK_SNAPSHOT_RESOURCE_URN,
            poa_plan["plan_urn"],
            dry_receipt["receipt_urn"],
        ):
            read_msg = handle_jsonrpc_message(
                {"jsonrpc": "2.0", "id": 10, "method": "resources/read", "params": {"uri": urn}},
                receipts_dir=receipts_dir,
                grants_dir=grants_dir,
            )
            if read_msg is None or "error" in read_msg:
                raise RuntimeError(f"CANARY_RESOURCE_READ_FAILED: {urn}")

        # 5. Idempotency conflict check on altered payload
        conflict_caught = False
        try:
            task_execute(
                "fixos://cleanup/auto",
                {"dry_run": True, "include_projects": True},
                registry_digest=digest,
                request_id="canary-preview-1",
                receipts_dir=receipts_dir,
                grants_dir=grants_dir,
            )
        except ValueError as exc:
            conflict_caught = "IDEMPOTENCY_CONFLICT" in str(exc)
        if not conflict_caught:
            raise RuntimeError("CANARY_IDEMPOTENCY_CONFLICT_NOT_CAUGHT")

        return {
            "passed": True,
            "handshake_verified": True,
            "nl_negative_guards_verified": True,
            "poa_ungranted_mutation_blocked": True,
            "urn_resources_verified": 4,
            "idempotency_conflict_verified": True,
            "sample_grant_urn": grant["grant_urn"],
        }


def run_conformance_and_runtime_canary(repo_root: Path | None = None) -> dict[str, Any]:
    """Run static conformance + runtime canary and report all three evidence tiers distinctly."""
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    declared = inspect_declared_requirements(root)
    parity = verify_capability_parity()
    v1_doc = export_mcp_registry_v1()
    fastmcp_check = verify_no_unsupported_fastmcp_declarations(root)
    runtime = run_observed_runtime_canary()

    return {
        "schema": CANARY_REPORT_SCHEMA,
        "declared_adoption": declared,
        "static_checkers": {
            "passed": True,
            "capability_parity": parity,
            "registry_v1_operation_count": len(v1_doc["operations"]),
            "fastmcp_hygiene": fastmcp_check,
        },
        "observed_runtime_canary": runtime,
    }
