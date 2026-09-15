"""Safety regressions for `fixos cleanup` found on a real developer machine."""

from __future__ import annotations

import shlex
import subprocess

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

        # 2 = individual; Docker yes; Npm yes. No protected-data confirmation
        # is needed because nothing is executed.
        result = CliRunner().invoke(command, input="2\ny\ny\n")

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

    def test_specialized_cleanup_paths_receive_dry_run(self, monkeypatch):
        calls = []

        def fake_ollama(self, *, days, dry_run):
            calls.append(("ollama-old", days, dry_run))
            return {"success": True, "space_freed_gb": 0}

        def fake_docker(self, *, dry_run, include_networks):
            calls.append(("docker-unused", dry_run, include_networks))
            return {"success": True, "space_freed_gb": 0}

        monkeypatch.setattr(ServiceCleaner, "cleanup_ollama_old_unused", fake_ollama)
        monkeypatch.setattr(ServiceCleaner, "cleanup_docker_unused", fake_docker)

        cleanup_cmd._execute_planned_cleanup(
            object(), {"cleanup_kind": "ollama-old", "days": 30}, dry_run=True
        )
        cleanup_cmd._execute_planned_cleanup(
            object(), {"cleanup_kind": "docker-unused"}, dry_run=True
        )

        assert calls == [
            ("ollama-old", 30, True),
            ("docker-unused", True, True),
        ]


class TestCleanupCommandSafety:
    def test_logs_service_leaves_xdg_state_alone(self):
        path = "~/.cache/log"
        assert ServiceDataScanner.SERVICE_PATHS[ServiceType.LOGS] == [path]
        assert ".local/state" not in ServiceCleaner.get_cleanup_command(ServiceType.LOGS, path)
        assert ".local/state" not in ServiceCleaner.get_preview_command(ServiceType.LOGS, path)

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


class TestScanMeasurement:
    def test_du_total_is_kept_when_a_subdirectory_is_unreadable(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="2048\t/data\n", stderr="denied")

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
