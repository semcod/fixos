"""Safety regressions for `fixos cleanup` found on a real developer machine."""

from __future__ import annotations

import shlex
import subprocess
from types import SimpleNamespace

import click
from click.testing import CliRunner

from fixos.cli import cleanup_cmd
from fixos.diagnostics import service_scanner
from fixos.diagnostics.service_cleanup import ServiceCleaner
from fixos.diagnostics.service_scanner import ServiceDataScanner, ServiceType


def _service(name, risk):
    service_type = name.lower()
    return {
        "service_type": service_type,
        "name": name,
        "path": f"/data/{service_type}",
        "size_mb": 1024,
        "size_gb": 1.0,
        "description": name,
        "can_cleanup": True,
        "cleanup_command": f"clean-{service_type}",
        "preview_command": f"show-{service_type}",
        "safe_to_cleanup": risk == "safe",
        "risk_level": risk,
        "details": {},
    }


class RecordingScanner:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def cleanup_service(self, service_type, dry_run, planned_service):
        self.calls.append((service_type, dry_run))
        return {
            "success": True,
            "space_freed_gb": 1.0,
            "output": f"[DRY RUN] Would execute: {planned_service['cleanup_command']}",
        }


def _plan(*services):
    safe = [svc for svc in services if svc["risk_level"] == "safe"]
    return {
        "threshold_mb": 500,
        "services_found": len(services),
        "total_size_gb": float(len(services)),
        "safe_cleanup_gb": float(len(safe)),
        "requires_review_gb": 0.0,
        "dangerous_gb": 0.0,
        "services": list(services),
        "safe_to_cleanup": safe,
        "requires_review": [],
        "dangerous": [svc for svc in services if svc["risk_level"] == "dangerous"],
        "warnings": [],
    }


class TestInteractiveDryRun:
    def test_terminal_escape_sequence_does_not_corrupt_choice(self):
        service = _service("Npm", "safe")

        @click.command()
        def command():
            mode, selected = cleanup_cmd._select_safe_services([service])
            assert mode == "safe"
            assert selected == [service]

        result = CliRunner().invoke(command, input="\x1b[F1\n")

        assert result.exit_code == 0, result.output
        assert "Invalid value" not in result.output

    def test_terminal_escape_sequence_is_removed_from_individual_selection(self):
        service = _service("Npm", "safe")

        @click.command()
        def command():
            selected = cleanup_cmd._select_individual_services([service])
            assert selected == [service]

        result = CliRunner().invoke(command, input="\x1b[F1\n")

        assert result.exit_code == 0, result.output
        assert "Invalid value" not in result.output

    def test_csi_navigation_sequence_is_removed_from_prompt_value(self):
        assert cleanup_cmd._clean_terminal_input("\x1b[1;5D1") == "1"

    def test_bulk_safe_choice_only_simulates(self):
        scanner = RecordingScanner()
        plan = _plan(_service("Npm", "safe"), _service("Pip", "safe"))

        @click.command()
        def command():
            cleanup_cmd._run_interactive_cleanup(plan, False, scanner, dry_run=True)

        result = CliRunner().invoke(command, input="1\n")

        assert result.exit_code == 0, result.output
        assert scanner.calls == [("npm", True), ("pip", True)]
        assert "Symulacja — nic nie usunięto." in result.output
        assert "Zwolniono" not in result.output

    def test_individual_choice_simulates_protected_entry_without_confirmation(self):
        scanner = RecordingScanner()
        plan = _plan(_service("Docker", "dangerous"), _service("Npm", "safe"))

        @click.command()
        def command():
            cleanup_cmd._run_interactive_cleanup(plan, False, scanner, dry_run=True)

        # 2 = individual; 'all' picks both entries in one input. No
        # protected-data confirmation is needed because nothing is executed.
        result = CliRunner().invoke(command, input="2\nall\n")

        assert result.exit_code == 0, result.output
        assert scanner.calls == [("docker", True), ("npm", True)]
        assert "Zwolniono" not in result.output

    def test_cli_dry_run_flag_reaches_interactive_cleanup(self, monkeypatch):
        scanner = RecordingScanner()
        plan = _plan(_service("Npm", "safe"))
        scanner.get_cleanup_plan = lambda selected_services=None: plan
        monkeypatch.setattr(cleanup_cmd, "ServiceDataScanner", lambda **_: scanner)

        result = CliRunner().invoke(
            cleanup_cmd.cleanup_services, ["--dry-run"], input="1\n"
        )

        assert result.exit_code == 0, result.output
        assert scanner.calls == [("npm", True)]
        assert "Tryb symulacji (--dry-run)" in result.output

    def test_incomplete_dry_run_result_fails_closed(self):
        @click.command()
        def command():
            cleanup_cmd._display_dry_run_result({})

        result = CliRunner().invoke(command)

        assert result.exit_code == 0, result.output
        assert "Błąd: nieznany błąd" in result.output
        assert "Symulacja" not in result.output

    def test_success_without_space_estimate_fails_closed(self):
        @click.command()
        def command():
            cleanup_cmd._display_dry_run_result({"success": True})

        result = CliRunner().invoke(command)

        assert result.exit_code == 0, result.output
        assert "niekompletny wynik symulacji" in result.output
        assert "Symulacja" not in result.output


class TestYesFlag:
    """`--yes` runs the safe plan with zero interactive input."""

    def _command_with_plan(self, plan, scanner, monkeypatch, argv):
        scanner.get_cleanup_plan = lambda selected_services=None: plan
        monkeypatch.setattr(cleanup_cmd, "ServiceDataScanner", lambda **_: scanner)
        return CliRunner().invoke(cleanup_cmd.cleanup_services, argv)

    def test_yes_runs_all_safe_without_input(self, monkeypatch):
        scanner = RecordingScanner()
        plan = _plan(_service("Npm", "safe"), _service("Pip", "safe"))
        result = self._command_with_plan(plan, scanner, monkeypatch, ["--yes"])
        assert result.exit_code == 0, result.output
        assert scanner.calls == [("npm", False), ("pip", False)]

    def test_yes_dry_run_simulates_everything(self, monkeypatch):
        scanner = RecordingScanner()
        plan = _plan(_service("Npm", "safe"), _service("Pip", "safe"))
        result = self._command_with_plan(
            plan, scanner, monkeypatch, ["--yes", "--dry-run"]
        )
        assert result.exit_code == 0, result.output
        assert scanner.calls == [("npm", True), ("pip", True)]
        assert "Tryb symulacji (--dry-run)" in result.output
        assert "Zwolniono" not in result.output

    def test_yes_with_no_safe_services_cleans_nothing(self, monkeypatch):
        scanner = RecordingScanner()
        plan = _plan(_service("Docker", "dangerous"))
        result = self._command_with_plan(plan, scanner, monkeypatch, ["--yes"])
        assert result.exit_code == 0, result.output
        assert scanner.calls == []
        assert "Brak bezpiecznych pozycji" in result.output


class TestCleanupCommandSafety:
    def test_logs_service_leaves_xdg_state_alone(self):
        path = "~/.cache/log"
        assert ServiceDataScanner.SERVICE_PATHS[ServiceType.LOGS] == [path]
        assert ".local/state" not in ServiceCleaner.get_cleanup_command(
            ServiceType.LOGS, path
        )
        assert ".local/state" not in ServiceCleaner.get_preview_command(
            ServiceType.LOGS, path
        )

    def test_multi_word_cache_paths_stay_single_rm_arguments(self):
        for service_type in (ServiceType.DISCORD, ServiceType.SLACK):
            command = ServiceCleaner.get_cleanup_command(service_type, "")
            words = shlex.split(command)
            assert words[:2] == ["rm", "-rf"]
            assert all(word.startswith("~/.config/") for word in words[2:]), words

    def test_gcloud_cache_cleanup_keeps_credentials(self):
        command = ServiceCleaner.get_cleanup_command(ServiceType.GCLOUD, "")
        assert "revoke" not in command
        assert "gcloud auth" not in command

    def test_spotify_offline_data_is_review_only_and_has_no_bulk_command(self):
        offline = "~/.config/spotify/Data"
        assert ServiceCleaner.get_risk_level(ServiceType.SPOTIFY, offline) == "review"
        assert ServiceCleaner.get_cleanup_command(ServiceType.SPOTIFY, offline) == ""

    def test_discovered_cache_command_is_bounded_to_xdg_roots(self):
        safe = ServiceCleaner.get_cleanup_command(
            ServiceType.GENERIC_CACHE, "~/.cache/example cache"
        )
        outside = ServiceCleaner.get_cleanup_command(ServiceType.GENERIC_CACHE, "/tmp/cache")

        assert safe.startswith("rm -rf -- ")
        assert "example cache" in safe
        assert outside == ""


class TestDockerDefaultProposal:
    """Default `fixos cleanup` must propose stopped containers and unused
    images without touching running containers or volumes."""

    @staticmethod
    def _scanner(usage):
        class FakeScanner:
            def scan_service(self, service_type):
                if service_type == ServiceType.DOCKER:
                    return [SimpleNamespace(details={"usage": usage})]
                return []

        return FakeScanner()

    @staticmethod
    def _cleaner(scanner, monkeypatch):
        cleaner = ServiceCleaner(scanner)
        monkeypatch.setattr(cleaner, "list_ollama_models", list)
        monkeypatch.setattr(cleaner, "list_running_ollama_models", lambda: set())
        monkeypatch.setattr(
            cleaner,
            "cleanup_docker_networks",
            lambda days=0, dry_run=False: {
                "success": True,
                "candidates": [],
                "removed": [],
                "failed": [],
            },
        )
        return cleaner

    def test_default_plan_proposes_stopped_containers_and_images(self, monkeypatch):
        usage = {
            "Containers": {"size_gb": 3.0, "reclaimable_gb": 2.5},
            "Images": {"size_gb": 40.0, "reclaimable_gb": 10.0},
            "Build Cache": {"size_gb": 5.0, "reclaimable_gb": 4.0},
        }
        cleaner = self._cleaner(self._scanner(usage), monkeypatch)

        actions = cleaner.build_safe_age_actions()
        kinds = {action["cleanup_kind"] for action in actions}

        assert "docker-containers" in kinds
        assert "docker-unused" in kinds

        containers = next(
            action
            for action in actions
            if action["cleanup_kind"] == "docker-containers"
        )
        assert containers["safe_to_cleanup"] is True
        assert containers["risk_level"] == "safe"
        assert containers["size_gb"] == 2.5
        assert containers["cleanup_command"] == "docker container prune --force"

    def test_container_proposal_absent_without_reclaimable(self, monkeypatch):
        usage = {
            "Containers": {"size_gb": 3.0, "reclaimable_gb": 0.0},
            "Images": {"size_gb": 40.0, "reclaimable_gb": 0.0},
            "Build Cache": {"size_gb": 5.0, "reclaimable_gb": 0.0},
        }
        cleaner = self._cleaner(self._scanner(usage), monkeypatch)

        kinds = {action["cleanup_kind"] for action in cleaner.build_safe_age_actions()}
        assert "docker-containers" not in kinds
        assert "docker-unused" not in kinds

    def test_container_prune_never_touches_volumes_or_running(self):
        command = ServiceCleaner.get_docker_containers_command()

        assert command == "docker container prune --force"
        assert "volume" not in command
        assert "system prune" not in command
        assert "image" not in command

    def test_container_prune_dry_run_executes_nothing(self, monkeypatch):
        def forbidden_run(*args, **kwargs):
            raise AssertionError("dry-run must not execute docker commands")

        monkeypatch.setattr(subprocess, "run", forbidden_run)
        usage = {"Containers": {"size_gb": 3.0, "reclaimable_gb": 2.5}}
        cleaner = self._cleaner(self._scanner(usage), monkeypatch)

        result = cleaner.cleanup_docker_containers(dry_run=True)

        assert result["success"] is True
        assert result["space_freed_gb"] == 2.5
        assert "docker container prune --force" in result["output"]

    def test_planned_cleanup_dispatches_containers_kind(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            ServiceCleaner,
            "cleanup_docker_containers",
            lambda self, dry_run=False: (
                calls.append(dry_run)
                or {"success": True, "space_freed_gb": 0.0, "output": ""}
            ),
        )
        svc = _service("Docker (zatrzymane kontenery)", "safe")
        svc["cleanup_kind"] = "docker-containers"
        svc["service_type"] = "docker-containers"

        cleanup_cmd._execute_planned_cleanup(object(), svc, dry_run=True)

        assert calls == [True]


class TestScanMeasurement:
    def test_du_total_is_kept_when_a_subdirectory_is_unreadable(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="2048\t/data\n", stderr="denied"
            )

        def forbidden_walk(*args, **kwargs):
            raise AssertionError("du output must not be discarded")

        monkeypatch.setattr(service_scanner.subprocess, "run", fake_run)
        monkeypatch.setattr(service_scanner.os, "walk", forbidden_walk)

        assert ServiceDataScanner()._get_path_size_mb("/data") == 2.0

    def test_docker_usage_timeout_runs_once_and_is_reported(self, monkeypatch):
        calls = []

        def slow_docker(cmd, **kwargs):
            calls.append(cmd)
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

        monkeypatch.setattr(service_scanner.subprocess, "run", slow_docker)
        scanner = ServiceDataScanner()

        assert scanner._get_docker_daemon_usage() is None
        assert scanner._get_docker_daemon_size_mb() is None
        assert len(calls) == 1
        assert len(scanner.scan_warnings) == 1
        assert "docker system df" in scanner.scan_warnings[0]

        assert scanner._get_docker_daemon_usage(refresh=True) is None
        assert len(calls) == 2

    def test_scan_warnings_reach_plan_and_summary(self, monkeypatch):
        scanner = ServiceDataScanner()
        scanner.scan_warnings.append("Docker: pominięto")
        monkeypatch.setattr(scanner, "scan_all_services", lambda: [])
        cleaner = ServiceCleaner(scanner)
        monkeypatch.setattr(cleaner, "build_safe_age_actions", lambda selected=None: [])

        plan = cleaner.get_cleanup_plan()

        assert plan["warnings"] == ["Docker: pominięto"]

        @click.command()
        def command():
            cleanup_cmd._display_cleanup_summary(plan, 500)

        result = CliRunner().invoke(command)
        assert "Docker: pominięto" in result.output
        assert "Nie znaleziono usług powyżej progu." in result.output
# ruff: noqa: PIE807


class TestJetBrainsHistoryProtection:
    def test_system_directory_is_protected(self):
        assert ServiceCleaner.get_risk_level(ServiceType.JETBRAINS) == "dangerous"

    def test_explicit_selection_has_no_bulk_delete_command(self):
        assert ServiceCleaner.get_cleanup_command(ServiceType.JETBRAINS, "/home/test/.cache/JetBrains") == ""

    def test_scanner_protects_system_data_and_retains_preview(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        monkeypatch.setattr(scanner, "measure_service_size_mb", lambda *args: 1024)
        monkeypatch.setattr(scanner._details_provider, "get_details", lambda *args: {})
        entry = scanner._analyze_service_path(ServiceType.JETBRAINS, "/home/test/.cache/JetBrains")
        assert entry.risk_level == "dangerous"
        assert not entry.safe_to_cleanup
        assert not entry.can_cleanup
        assert not entry.cleanup_command
        assert "du -sh" in entry.preview_command

    def test_stale_safe_plan_cannot_execute_bulk_cleanup(self, monkeypatch):
        def unexpected_execution(*args, **kwargs):
            raise AssertionError("JetBrains cleanup must not execute commands")

        monkeypatch.setattr(subprocess, "run", unexpected_execution)
        cleaner = ServiceCleaner(None)
        stale_plan = _service("Jetbrains", "safe")
        result = cleaner.cleanup_service("jetbrains", planned_service=stale_plan)
        assert not result["success"]
        assert "zbiorcze czyszczenie" in result["error"]
        preview = cleaner.cleanup_service("jetbrains", dry_run=True, planned_service=stale_plan)
        assert preview["success"]
        assert preview["requires_item_selection"]
        assert "clean-jetbrains" not in preview["output"]
