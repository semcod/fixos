"""
Testy jednostkowe – config, anonimizacja, web search.
"""

from __future__ import annotations

import os
from unittest.mock import patch


class TestConfig:
    def test_default_provider_is_gemini(self):
        from fixos.config import FixOsConfig

        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}, clear=False):
            cfg = FixOsConfig.load()
        assert cfg.provider == "gemini"

    def test_model_default_gemini(self):
        from fixos.config import FixOsConfig

        cfg = FixOsConfig.load(provider="gemini")
        assert "gemini" in cfg.model.lower()

    def test_invalid_provider_fallback(self):
        from fixos.config import FixOsConfig

        with patch.dict(os.environ, {"LLM_PROVIDER": "nonexistent"}, clear=False):
            cfg = FixOsConfig.load()
        assert cfg.provider == "gemini"

    def test_validate_missing_key(self):
        from fixos.config import FixOsConfig

        cfg = FixOsConfig(provider="openai", api_key=None)
        errors = cfg.validate()
        assert len(errors) > 0
        assert "API" in errors[0]

    def test_validate_ollama_no_key_needed(self):
        from fixos.config import FixOsConfig

        cfg = FixOsConfig(provider="ollama", api_key=None)
        errors = cfg.validate()
        assert len(errors) == 0

    def test_agent_mode_from_env(self):
        from fixos.config import FixOsConfig

        with patch.dict(os.environ, {"AGENT_MODE": "autonomous"}, clear=False):
            cfg = FixOsConfig.load()
        assert cfg.agent_mode == "autonomous"

    def test_summary_masks_key(self):
        from fixos.config import FixOsConfig

        cfg = FixOsConfig(**{"api_key": "testAIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ12345"})
        summary = cfg.summary()
        assert "testAIza" in summary
        assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ12345" not in summary


class TestAnonymizer:
    def test_empty_string(self):
        from fixos.utils.anonymizer import anonymize

        anon, report = anonymize("")
        assert anon == ""
        assert len(report.replacements) == 0

    def test_non_string_input(self):
        from fixos.utils.anonymizer import anonymize

        anon, report = anonymize({"key": "value"})
        assert isinstance(anon, str)

    def test_no_sensitive_data(self):
        from fixos.utils.anonymizer import anonymize

        data = "systemctl status pipewire -- Active: running"
        anon, report = anonymize(data)
        # Brak IP ani ścieżek → brak lub minimalne zastąpienia
        sensitive_replacements = {
            k: v
            for k, v in report.replacements.items()
            if k not in ("Hostname", "Username")
        }
        assert len(sensitive_replacements) == 0

    def test_ipv6_not_mangled(self):
        """IPv6 adresy nie powinny być uszkodzone (nie obsługujemy)."""
        from fixos.utils.anonymizer import anonymize

        data = "IPv6 address: 2001:db8::1"
        anon, _ = anonymize(data)
        # Nie crashuje
        assert isinstance(anon, str)

    def test_multiple_ips_all_masked(self):
        from fixos.utils.anonymizer import anonymize

        data = "from 192.168.1.1 to 10.0.0.50 via 172.16.0.1"
        anon, report = anonymize(data)
        assert report.replacements.get("Adresy IPv4", 0) == 3
        assert "192.168.1.1" not in anon
        assert "10.0.0.50" not in anon

    def test_password_in_env_masked(self):
        from fixos.utils.anonymizer import anonymize

        data = "DB_PASSWORD=test_password_value " + "API_" + "KEY=test_api_key_value"
        anon, report = anonymize(data)
        assert "test_password_value" not in anon
        assert report.replacements.get("Hasła/sekrety", 0) > 0


class TestWebSearch:
    def test_format_empty_results(self):
        from fixos.utils.web_search import format_results_for_llm

        result = format_results_for_llm([])
        assert "Brak" in result

    def test_format_single_result(self):
        from fixos.utils.web_search import SearchResult, format_results_for_llm

        r = SearchResult(
            title="Fix Lenovo audio",
            url="https://example.com",
            snippet="Install sof-firmware",
            source="Test",
        )
        formatted = format_results_for_llm([r])
        assert "Fix Lenovo audio" in formatted
        assert "https://example.com" in formatted
        assert "[1]" in formatted

    def test_http_get_timeout(self):
        """_http_get powinien obsłużyć timeout gracefully."""
        from fixos.utils.web_search import _http_get

        result = _http_get("http://240.0.0.1/nonexistent", timeout=1)
        assert result is None


class TestSortFixesByPriority:
    def test_cleanup_before_upgrade(self):
        from fixos.agent.session_handlers import _sort_fixes_by_priority

        fixes = [
            ("sudo dnf upgrade -y", "upgrade"),
            ("sudo journalctl --vacuum-size=200M", "clean logs"),
        ]
        result = _sort_fixes_by_priority(fixes)
        assert result[0][0] == "sudo journalctl --vacuum-size=200M"
        assert result[1][0] == "sudo dnf upgrade -y"

    def test_disk_hungry_sorted_to_end(self):
        from fixos.agent.session_handlers import _sort_fixes_by_priority

        fixes = [
            ("sudo dnf upgrade -y", "upgrade"),
            ("sudo apt full-upgrade -y", "upgrade"),
            ("sudo dnf remove oldkernel", "remove"),
            ("sudo rm -rf /var/cache", "clean cache"),
        ]
        result = _sort_fixes_by_priority(fixes)
        # Both remove and rm are cleanup (score 0), upgrades are score 2.
        # Stable sort preserves original order among equal scores.
        assert result[0][0] == "sudo dnf remove oldkernel"
        assert result[1][0] == "sudo rm -rf /var/cache"
        assert result[2][0] == "sudo dnf upgrade -y"
        assert result[3][0] == "sudo apt full-upgrade -y"

    def test_unknown_commands_mid_priority(self):
        from fixos.agent.session_handlers import _sort_fixes_by_priority

        fixes = [
            ("sudo dnf upgrade -y", "upgrade"),
            ("echo 'restart service'", "info"),
        ]
        result = _sort_fixes_by_priority(fixes)
        assert result[0][0] == "echo 'restart service'"
        assert result[1][0] == "sudo dnf upgrade -y"


class TestDiagnosticOnlyCommand:
    def test_simple_diagnostic_is_filtered(self):
        from fixos.agent.session_core import _is_diagnostic_only_command

        assert _is_diagnostic_only_command("df -h") is True
        assert _is_diagnostic_only_command("free -h") is True
        assert _is_diagnostic_only_command("systemctl status auditd") is True

    def test_repair_command_is_not_diagnostic(self):
        from fixos.agent.session_core import _is_diagnostic_only_command

        assert _is_diagnostic_only_command("sudo systemctl restart auditd") is False
        assert _is_diagnostic_only_command("dnf upgrade -y") is False
        assert _is_diagnostic_only_command("rm -rf /var/cache") is False

    def test_journalctl_vacuum_is_not_diagnostic(self):
        from fixos.agent.session_core import _is_diagnostic_only_command

        assert _is_diagnostic_only_command("journalctl --vacuum-size=200M") is False
        assert _is_diagnostic_only_command("journalctl --flush") is False

    def test_compound_command_any_repair_keeps_all(self):
        from fixos.agent.session_core import _is_diagnostic_only_command

        # Compound with both diagnostic and repair → not filtered
        assert _is_diagnostic_only_command("df -h && sudo dnf remove kernel") is False
        assert (
            _is_diagnostic_only_command("cat /etc/fstab || systemctl restart auditd")
            is False
        )

    def test_compound_all_diagnostic_is_filtered(self):
        from fixos.agent.session_core import _is_diagnostic_only_command

        assert _is_diagnostic_only_command("df -h && free -h") is True


class TestExtractFixes:
    """Regression tests for extract_fixes – covers multiple LLM output formats."""

    def test_strict_bold_backticks(self):
        """Pattern 1: **Komenda:** `command` **Co robi:** explanation"""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 **Problem 1: disk full**\n"
            "   **Komenda:** `sudo dnf autoremove -y`\n"
            "   **Co robi:** removes unused packages\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) == 1
        assert fixes[0][0] == "sudo dnf autoremove -y"

    def test_backticks_no_bold(self):
        """Pattern 2: Komenda: `command` (backticks, no bold)"""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 Problem 1: disk full\n"
            "Komenda: `sudo dnf autoremove -y`\n"
            "Co robi: removes unused packages\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) == 1
        assert fixes[0][0] == "sudo dnf autoremove -y"

    def test_no_backticks_no_bold(self):
        """Pattern 3: Komenda: command (plain text – deepseek bug scenario)"""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 **Problem 1: Krytyczne zapełnienie dysku.**\n"
            "Komenda: sudo journalctl --vacuum-size=200M && sudo dnf autoremove -y\n"
            "Co robi: Oczyszcza logi i pakiety.\n"
            "🟡 **Problem 2: swap failed.**\n"
            "Komenda: sudo systemctl restart swapfile.swap\n"
            "Co robi: Restartuje swap.\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) == 2
        assert "journalctl" in fixes[0][0]
        assert "swapfile" in fixes[1][0]

    def test_multiline_command_collapsed(self):
        """Pattern 3 with multiline command – should be collapsed to single line."""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 **Problem 1: disk full.**\n"
            "Komenda: sudo journalctl --vacuum-size=200M && sudo rm -rf\n"
            "/var/cache/abrt-diag/* && sudo dnf autoremove -y\n"
            "Co robi: cleanup\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) >= 1
        cmd = fixes[0][0]
        assert "\n" not in cmd
        assert "journalctl" in cmd
        assert "dnf autoremove" in cmd

    def test_co_robi_extracted_as_comment(self):
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 Problem 1: disk\n"
            "Komenda: `sudo dnf autoremove -y`\n"
            "Co robi: removes unused packages\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) == 1
        assert "removes" in fixes[0][1]

    def test_diagnostic_only_filtered(self):
        """Read-only commands should be filtered out."""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🔴 Problem 1: check disk\n"
            "   **Komenda:** `df -h`\n"
            "   **Co robi:** shows disk usage\n"
        )
        fixes = extract_fixes(reply)
        assert len(fixes) == 0

    def test_duplicate_commands_deduplicated(self):
        """Same command for multiple problems should appear only once."""
        from fixos.agent.session_core import extract_fixes

        reply = (
            "🟡 Problem 3: pending updates\n"
            "Komenda: sudo dnf upgrade -y\n"
            "Co robi: updates packages\n"
            "🟡 Problem 4: security patches\n"
            "Komenda: sudo dnf upgrade -y\n"
            "Co robi: same\n"
        )
        fixes = extract_fixes(reply)
        cmds = [cmd for cmd, _ in fixes]
        assert cmds.count("sudo dnf upgrade -y") == 1

    def test_empty_reply(self):
        from fixos.agent.session_core import extract_fixes

        assert extract_fixes("") == []
        assert extract_fixes("No problems found.") == []


def _remediation_reply() -> str:
    import json

    plan = {
        "schema": "fixos.remediation-plan/v1",
        "mode": "PLAN",
        "findings": [
            {
                "ref": "finding:fixos:root-space-critical",
                "severity": "CRITICAL",
                "category": "STORAGE",
                "title": "Krytycznie mało miejsca na partycji root",
                "evidence": ["root.used_percent=99.9", "root.free_gb=1.2"],
                "strategies": [
                    {
                        "id": "journal-recovery",
                        "label": "Ogranicz journal",
                        "risk": "LOW",
                        "recommended": True,
                        "commands": ["sudo journalctl --vacuum-size=500M"],
                        "verification": ["df -h /", "journalctl --disk-usage"],
                        "explanation": "Odzyskuje miejsce bez usuwania aktywnych logów.",
                    },
                    {
                        "id": "apt-cache-recovery",
                        "label": "Wyczyść cache APT",
                        "risk": "LOW",
                        "recommended": False,
                        "commands": ["sudo apt-get clean"],
                        "verification": ["du -sh /var/cache/apt"],
                        "explanation": "Usuwa pakiety, które można pobrać ponownie.",
                    },
                ],
            },
            {
                "ref": "finding:fixos:logrotate-failed",
                "severity": "ERROR",
                "category": "RUNTIME",
                "title": "Usługa logrotate jest w stanie failed",
                "evidence": ["systemd.logrotate=failed"],
                "strategies": [
                    {
                        "id": "restart-logrotate",
                        "label": "Uruchom logrotate ponownie",
                        "risk": "CAUTION",
                        "recommended": True,
                        "commands": ["sudo systemctl restart logrotate.service"],
                        "verification": ["systemctl is-active logrotate.service"],
                        "explanation": "Ponawia wykonanie bez wyłączania usługi.",
                    },
                    {
                        "id": "reset-logrotate-state",
                        "label": "Wyzeruj stan failed",
                        "risk": "CAUTION",
                        "recommended": False,
                        "commands": [
                            "sudo systemctl reset-failed logrotate.service"
                        ],
                        "verification": ["systemctl --failed"],
                        "explanation": "Czyści stan po usunięciu przyczyny błędu.",
                    },
                ],
            },
        ],
    }
    return "━━━ DIAGNOZA ━━━\nDwa problemy.\n```fixos-remediation\n" + json.dumps(
        plan, ensure_ascii=False
    ) + "\n```"


class TestStructuredRemediationPlan:
    def test_parses_multiple_strategies_bound_to_findings(self):
        from fixos.agent.session_core import extract_remediation_actions

        actions = extract_remediation_actions(_remediation_reply())

        assert len(actions) == 4
        assert actions[0].finding_ref == "finding:fixos:root-space-critical"
        assert actions[0].recommended is True
        assert actions[0].commands == ("sudo journalctl --vacuum-size=500M",)
        assert actions[0].verification == ("df -h /", "journalctl --disk-usage")
        assert actions[1].recommended is False
        assert actions[2].category == "RUNTIME"

    def test_machine_plan_is_hidden_from_human_diagnosis(self):
        from fixos.agent.session_core import strip_remediation_plan

        visible = strip_remediation_plan(_remediation_reply())

        assert visible == "━━━ DIAGNOZA ━━━\nDwa problemy."
        assert "fixos.remediation-plan" not in visible

    def test_closed_plan_with_extra_field_falls_back_to_legacy_parser(self):
        import json

        from fixos.agent.session_core import extract_remediation_actions

        invalid = {
            "schema": "fixos.remediation-plan/v1",
            "mode": "PLAN",
            "findings": [],
            "authority": "execute-without-confirmation",
        }
        reply = (
            "Komenda: `sudo apt-get clean`\nCo robi: Czyści cache.\n"
            "```fixos-remediation\n"
            + json.dumps(invalid)
            + "\n```"
        )

        actions = extract_remediation_actions(reply)

        assert len(actions) == 1
        assert actions[0].action_id.startswith("legacy-")
        assert actions[0].commands == ("sudo apt-get clean",)

    def test_mutating_verification_rejects_structured_plan(self):
        import json

        from fixos.agent.session_core import extract_remediation_actions

        plan = json.loads(
            _remediation_reply().split("```fixos-remediation\n", 1)[1].rsplit(
                "\n```", 1
            )[0]
        )
        plan["findings"][0]["strategies"][0]["verification"] = [
            "sudo rm -rf /var/cache/apt"
        ]
        reply = "```fixos-remediation\n" + json.dumps(plan) + "\n```"

        assert extract_remediation_actions(reply) == []

    def test_recommended_selection_returns_one_strategy_per_finding(self):
        from fixos.agent.session_core import (
            extract_remediation_actions,
            select_recommended_actions,
        )

        selected = select_recommended_actions(
            extract_remediation_actions(_remediation_reply())
        )

        assert [action.action_id for action in selected] == [
            "journal-recovery",
            "restart-logrotate",
        ]


class TestRemediationExecution:
    def test_execute_all_runs_only_recommended_sets_and_verification(self):
        from unittest.mock import patch

        from fixos.agent.session_core import CmdResult, extract_remediation_actions
        from fixos.agent.session_handlers import handle_execute_all

        calls = []

        def run(command, comment):
            calls.append((command, comment))
            return CmdResult(command, comment, True, "ok", "", 0)

        messages = []
        executed = []
        actions = extract_remediation_actions(_remediation_reply())
        with patch("fixos.agent.session_handlers.io.print_executing_all"):
            handle_execute_all(actions, messages, executed, run)

        assert [command for command, _ in calls] == [
            "sudo journalctl --vacuum-size=500M",
            "df -h /",
            "journalctl --disk-usage",
            "sudo systemctl restart logrotate.service",
            "systemctl is-active logrotate.service",
        ]
        assert "sudo apt-get clean" not in [command for command, _ in calls]
        assert len(messages) == 2
        assert '"rawOutputIncluded": false' in messages[0]["content"]
        assert "finding:fixos:root-space-critical" in messages[0]["content"]
        assert all(result.finding_ref for result in executed)

    def test_selected_bundle_stops_before_verification_after_failure(self):
        from fixos.agent.session_core import CmdResult, extract_remediation_actions
        from fixos.agent.session_handlers import handle_fix_by_number

        actions = extract_remediation_actions(_remediation_reply())
        first = actions[0]
        expanded = type(first)(
            **{
                **first.__dict__,
                "commands": (
                    "sudo apt-get clean",
                    "sudo journalctl --vacuum-size=500M",
                ),
            }
        )
        calls = []

        def run(command, comment):
            calls.append(command)
            ok = len(calls) == 1
            return CmdResult(command, comment, ok, "", "failed" if not ok else "", 1 - int(ok))

        messages = []
        executed = []
        handle_fix_by_number("1", [expanded], messages, executed, run)

        assert calls == [
            "sudo apt-get clean",
            "sudo journalctl --vacuum-size=500M",
        ]
        assert all(command not in calls for command in expanded.verification)
        assert '"outcome": "FAILED"' in messages[0]["content"]

    def test_execute_all_stops_after_first_failed_recommended_set(self):
        from unittest.mock import patch

        from fixos.agent.session_core import CmdResult, extract_remediation_actions
        from fixos.agent.session_handlers import handle_execute_all

        calls = []

        def run(command, comment):
            calls.append(command)
            return CmdResult(command, comment, False, "", "failed", 1)

        messages = []
        executed = []
        with patch("fixos.agent.session_handlers.io.print_executing_all"):
            handle_execute_all(
                extract_remediation_actions(_remediation_reply()),
                messages,
                executed,
                run,
            )

        assert calls == ["sudo journalctl --vacuum-size=500M"]
        assert len(messages) == 1
        assert '"outcome": "FAILED"' in messages[0]["content"]


class TestRemediationMenu:
    def test_menu_groups_strategies_and_labels_recommended_aggregate(self):
        import io

        from rich.console import Console

        from fixos.agent import session_io
        from fixos.agent.session_core import extract_remediation_actions

        output = io.StringIO()
        original_console = session_io.console
        session_io.console = Console(file=output, force_terminal=False, width=120)
        try:
            session_io.print_action_menu(
                extract_remediation_actions(_remediation_reply()), 120, 42
            )
        finally:
            session_io.console = original_console

        rendered = output.getvalue()
        assert "Krytycznie mało miejsca" in rendered
        assert "ZALECANE" in rendered
        assert "krok 1/1" in rendered
        assert "Weryfikacja:" in rendered
        assert "2 zestawów" in rendered


class TestAllModulesRegistered:
    """Verify all 9 diagnostic modules are registered."""

    def test_all_nine_modules_present(self):
        from fixos.diagnostics.system_checks import DIAGNOSTIC_MODULES

        expected = {
            "system",
            "audio",
            "thumbnails",
            "hardware",
            "security",
            "resources",
            "packages",
            "storage",
            "files",
        }
        assert set(DIAGNOSTIC_MODULES.keys()) == expected

    def test_all_modules_callable(self):
        from fixos.diagnostics.system_checks import DIAGNOSTIC_MODULES

        for key, (desc, fn) in DIAGNOSTIC_MODULES.items():
            assert callable(fn), f"Module {key} function is not callable"
            assert isinstance(desc, str) and len(desc) > 0, (
                f"Module {key} has empty description"
            )


class TestInteractiveBlocker:
    def test_newgrp_blocked(self):
        from fixos.platform_utils import is_interactive_blocker

        assert (
            is_interactive_blocker("sudo usermod -aG video $USER && newgrp video")
            is not None
        )

    def test_su_dash_blocked(self):
        from fixos.platform_utils import is_interactive_blocker

        assert is_interactive_blocker("su - tom") is not None

    def test_top_not_blocked_if_batch(self):
        from fixos.platform_utils import is_interactive_blocker

        assert is_interactive_blocker("top -b -n1") is None

    def test_regular_command_not_blocked(self):
        from fixos.platform_utils import is_interactive_blocker

        assert is_interactive_blocker("dnf upgrade -y") is None
