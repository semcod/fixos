import click
from click.testing import CliRunner
from types import SimpleNamespace

from fixos.cli import cleanup_cmd


def _service(name, risk, *, can_cleanup=True):
    service_type = name.lower()
    return {
        "service_type": service_type,
        "name": name,
        "path": f"/data/{service_type}",
        "size_mb": 1024,
        "size_gb": 1.0,
        "description": name,
        "can_cleanup": can_cleanup,
        "cleanup_command": f"clean-{service_type}" if can_cleanup else "",
        "preview_command": f"show-{service_type}",
        "safe_to_cleanup": risk == "safe",
        "risk_level": risk,
        "details": {},
    }


def test_individual_mode_walks_all_risk_tiers_in_display_order():
    safe = _service("Npm", "safe")
    review = _service("Jetbrains", "review")
    protected = _service("Docker", "dangerous")
    unavailable = _service("Ollama", "dangerous", can_cleanup=False)
    plan = {
        "services": [protected, review, safe, unavailable],
        "safe_to_cleanup": [safe],
        "requires_review": [review],
        "dangerous": [protected, unavailable],
    }
    calls = []

    class Scanner:
        def cleanup_service(self, service_type, dry_run, planned_service):
            calls.append((service_type, planned_service["path"]))
            return {"success": True, "space_freed_gb": 1}

    @click.command()
    def command():
        cleanup_cmd._run_interactive_cleanup(plan, False, Scanner())

    # 2 = individual; Docker yes; JetBrains no; Npm yes; Docker risk
    # confirmation yes. Ollama has no executable bulk action, so it is shown
    # but intentionally does not consume an answer.
    result = CliRunner().invoke(command, input="2\ny\nn\ny\ny\n")

    assert result.exit_code == 0
    individual_output = result.output.split(
        "Wybierz kolejno spośród wszystkich możliwych usług:", 1
    )[1]
    assert individual_output.index("Docker") < individual_output.index("Jetbrains")
    assert individual_output.index("Jetbrains") < individual_output.index("Npm")
    assert "Ollama" in individual_output
    assert "brak bezpiecznej operacji zbiorczej" in individual_output
    assert calls == [
        ("docker", "/data/docker"),
        ("npm", "/data/npm"),
    ]


def test_individual_mode_is_available_when_no_safe_services_exist():
    review = _service("Jetbrains", "review")
    plan = {
        "services": [review],
        "safe_to_cleanup": [],
        "requires_review": [review],
        "dangerous": [],
    }

    class Scanner:
        def cleanup_service(self, service_type, dry_run, planned_service):
            return {"success": True, "space_freed_gb": 0}

    @click.command()
    def command():
        cleanup_cmd._run_interactive_cleanup(plan, False, Scanner())

    result = CliRunner().invoke(command, input="n\n")

    assert result.exit_code == 0
    assert "Jetbrains" in result.output
    assert "Pominięto czyszczenie." in result.output


def test_docker_selection_does_not_promise_full_reclaimable_amount():
    docker = _service("Docker", "dangerous")
    docker["details"] = {
        "usage": {"Build Cache": {"reclaimable_gb": 64.73}},
    }

    description = cleanup_cmd._selection_description(docker)

    assert "Docker raportuje 64.73 GB" in description
    assert "filtr >7 dni zwykle usunie mniej" in description


def _entry(name, risk, *, can_cleanup):
    service_type = name.lower()
    return SimpleNamespace(
        service_type=SimpleNamespace(value=service_type),
        name=name,
        path=f"/data/{service_type}",
        size_mb=1024.0,
        size_gb=1.0,
        description=name,
        can_cleanup=can_cleanup,
        cleanup_command=f"clean-{service_type}" if can_cleanup else "",
        preview_command=f"show-{service_type}",
        safe_to_cleanup=risk == "safe",
        risk_level=risk,
        impact="high",
        items_count=None,
        details={},
    )


def test_single_service_protected_data_shows_preview_without_confirmation():
    protected = _entry("Lmstudio", "dangerous", can_cleanup=False)

    class Scanner:
        def scan_service(self, service_type):
            return [protected]

        def cleanup_service(self, *args, **kwargs):
            raise AssertionError("protected bulk cleanup must not execute")

    @click.command()
    def command():
        cleanup_cmd._cleanup_single_service("lmstudio", Scanner(), False, False)

    result = CliRunner().invoke(command)

    assert result.exit_code == 0
    assert "zbiorcze czyszczenie jest wyłączone" in result.output
    assert "Bezpieczny podgląd: show-lmstudio" in result.output
    assert "[y/N]" not in result.output


def test_single_service_prefers_safe_cache_over_protected_entry():
    protected = _entry("Vscode", "dangerous", can_cleanup=False)
    safe = _entry("Vscode", "safe", can_cleanup=True)
    safe.path = "/data/vscode-cache"
    calls = []

    class Scanner:
        def scan_service(self, service_type):
            return [protected, safe]

        def cleanup_service(self, service_type, dry_run, planned_service):
            calls.append(planned_service)
            return {"success": True, "space_freed_gb": 1.0, "output": ""}

    @click.command()
    def command():
        cleanup_cmd._cleanup_single_service("vscode", Scanner(), False, False)

    result = CliRunner().invoke(command)

    assert result.exit_code == 0
    assert calls[0]["path"] == "/data/vscode-cache"
    assert calls[0]["risk_level"] == "safe"
    assert "[y/N]" not in result.output


def test_single_docker_dry_run_marks_reclaimable_as_upper_bound():
    docker = _entry("Docker", "dangerous", can_cleanup=True)
    docker.cleanup_command = "docker builder prune --force --filter until=168h"

    class Scanner:
        def scan_service(self, service_type):
            return [docker]

        def cleanup_service(self, service_type, dry_run, planned_service):
            return {
                "success": True,
                "space_freed_gb": 64.73,
                "output": "[DRY RUN] Would execute: docker builder prune",
            }

    @click.command()
    def command():
        cleanup_cmd._cleanup_single_service("docker", Scanner(), False, True)

    result = CliRunner().invoke(command)

    assert result.exit_code == 0
    assert "Szacowane maksimum do odzyskania: 64.73 GB" in result.output
    assert "filtr >7 dni zwykle usunie mniej" in result.output
