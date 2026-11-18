"""Unit tests for shared NL-to-URI router (`wellmanifest.nl-plan/v1`) (#167)."""

from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner

from fixos.cli.main import cli
from fixos.mcp_server import task_plan
from fixos.nl_router import (
    NL_PLAN_SCHEMA,
    NL_PROFILE_ID,
    normalize_nl_text,
    route_nl_to_uri,
    validate_nl_plan_envelope,
)


def test_diacritic_normalization_and_pl_en_routing():
    assert normalize_nl_text("Wyczyść stary cache i żółte błędy łódki") == (
        "wyczysc stary cache i zolte bledy lodki"
    )

    pl_clean = task_plan("Wyczyść bezpieczny cache na dysku")
    assert pl_clean["schema"] == NL_PLAN_SCHEMA
    assert pl_clean["profile"] == NL_PROFILE_ID
    assert pl_clean["status"] == "ok"
    assert pl_clean["operation_id"] == "fixos://cleanup/auto"
    assert pl_clean["effect"] == "mutate"
    assert pl_clean["grants_authority"] is False
    assert pl_clean["executable"] is False

    en_disk = task_plan("show free disk space and cache size")
    assert en_disk["status"] == "ok"
    assert en_disk["operation_id"] == "fixos://diagnostics/disk"
    assert en_disk["effect"] == "read"

    en_project_disk = task_plan("show project disk space")
    assert en_project_disk["status"] == "ok"
    assert en_project_disk["operation_id"] == "fixos://diagnostics/projects"
    assert en_project_disk["effect"] == "read"

    pl_printers = task_plan("sprawdź drukarki sieciowe w CUPS")
    assert pl_printers["status"] == "ok"
    assert pl_printers["operation_id"] == "fixos://diagnostics/printers"


def test_negation_inquiry_standalone_auto_and_unknown_abstention():
    neg1 = task_plan("nie usuwaj żadnych plików ani cache automatycznie")
    assert neg1["status"] == "clarify"
    assert neg1["negation_detected"] is True
    assert neg1["operation_id"] is None
    assert neg1["effect"] == "none"

    neg_en = task_plan("do not delete any project caches")
    assert neg_en["status"] == "clarify"
    assert neg_en["operation_id"] is None

    read_no_clean = task_plan("sprawdź wolne miejsce na dysku, ale nie czyść nic")
    assert read_no_clean["status"] == "ok"
    assert read_no_clean["operation_id"] == "fixos://diagnostics/disk"
    assert read_no_clean["effect"] == "read"
    assert read_no_clean["negation_detected"] is True

    question = task_plan("czy wyczyścić cache na dysku?")
    assert question["status"] == "clarify"
    assert question["operation_id"] is None
    assert question["grants_authority"] is False

    for auto_prompt in ("auto", "tryb auto", "automatycznie", "run auto"):
        auto_res = task_plan(auto_prompt)
        assert auto_res["status"] == "clarify"
        assert auto_res["operation_id"] is None
        assert auto_res["grants_authority"] is False

    empty = task_plan("   ")
    assert empty["status"] == "clarify"
    assert empty["operation_id"] is None
    assert empty["confidence"] == 0.0

    unknown = task_plan("zamów pizzę hawajską na obiad")
    assert unknown["status"] == "unsupported"
    assert unknown["operation_id"] is None
    assert unknown["confidence"] == 0.0


def test_optional_llm_dsl_validation_fails_closed():
    ok_llm = route_nl_to_uri(
        "unusual phrasing about hardware sensors",
        llm_dsl_resolver=lambda _t, _uris: {
            "status": "ok",
            "operation_id": "fixos://plugins/hardware",
            "confidence": 0.82,
            "grants_authority": False,
        },
    )
    assert ok_llm["status"] == "ok"
    assert ok_llm["operation_id"] == "fixos://plugins/hardware"
    assert ok_llm["grants_authority"] is False

    with pytest.raises(ValueError, match="LLM_DSL_UNKNOWN_URI"):
        route_nl_to_uri(
            "run shell rm -rf",
            llm_dsl_resolver=lambda _t, _uris: {
                "status": "ok",
                "operation_id": "sh://rm/-rf",
            },
        )

    with pytest.raises(ValueError, match="LLM_DSL_AUTHORITY_FORBIDDEN"):
        route_nl_to_uri(
            "custom unrecognized directive",
            llm_dsl_resolver=lambda _t, _uris: {
                "status": "ok",
                "operation_id": "fixos://cleanup/auto",
                "grants_authority": True,
            },
        )

    with pytest.raises(ValueError, match="NL_PLAN_AUTHORITY_ESCALATION_FORBIDDEN"):
        validate_nl_plan_envelope({**ok_llm, "grants_authority": True})

    with pytest.raises(ValueError, match="NL_PLAN_UNKNOWN_FIELDS"):
        validate_nl_plan_envelope({**ok_llm, "shell_cmd": "rm -rf /"})

    with pytest.raises(ValueError, match="NL_PLAN_INCONSISTENT_OPERATION"):
        validate_nl_plan_envelope({**ok_llm, "operation": "fixos://cleanup/auto"})

    with pytest.raises(ValueError, match="NL_PLAN_INCONSISTENT_TOOL_NAME"):
        validate_nl_plan_envelope({**ok_llm, "tool_name": "cleanup_auto"})


def test_ask_cli_blocks_negated_mutation_using_shared_nl_router():
    runner = CliRunner()
    res = runner.invoke(cli, ["ask", "nie usuń kontenerów docker", "--dry-run"])
    assert res.exit_code == 0
    parsed = yaml.safe_load(res.output)
    assert parsed["status"] == "clarify"
    assert parsed["nl_plan"]["negation_detected"] is True
    assert "docker rm" not in str(parsed.get("command", ""))
