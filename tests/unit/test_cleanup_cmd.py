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


def test_docker_old_flag_routes_to_age_filtered_prune(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=30, dry_run=False, include_networks=False):
        captured["days"] = days
        captured["dry_run"] = dry_run
        captured["include_networks"] = include_networks
        return {
            "success": True,
            "command": f"docker image prune -a --force --filter until={days * 24}h",
            "output": "[DRY RUN] Would execute",
            "estimated_max_gb": 10.0,
            "space_freed_gb": 10.0,
            "days": days,
            "until_hours": days * 24,
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_old_unused",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--docker-old", "--days", "30", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "days": 30,
        "dry_run": True,
        "include_networks": True,
    }
    assert "nieużywane obrazy starsze niż 30 dni" in result.output
    assert "until=720h" in result.output


def test_docker_old_alias_via_cleanup_flag(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=30, dry_run=False, include_networks=False):
        captured["days"] = days
        captured["include_networks"] = include_networks
        return {
            "success": True,
            "command": "docker image prune -a --force --filter until=1440h",
            "output": "",
            "estimated_max_gb": 0,
            "space_freed_gb": 0,
            "days": days,
            "until_hours": days * 24,
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_old_unused",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["-c", "docker-old", "--days", "60", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured["days"] == 60
    assert captured["include_networks"] is True
    assert "60 dni" in result.output


def test_docker_all_cleans_unused_data_and_orphan_networks(monkeypatch):
    captured = {}

    def fake_cleanup(self, dry_run=False, include_networks=False):
        captured.update(
            dry_run=dry_run,
            include_networks=include_networks,
        )
        return {
            "success": True,
            "command": "docker image prune -a --force",
            "estimated_max_gb": 3.0,
            "space_freed_gb": 0,
            "network_cleanup": {
                "success": True,
                "min_age_days": 0,
                "candidates": [
                    {
                        "id": "a" * 64,
                        "short_id": "a" * 12,
                        "name": "old_default",
                        "age_days": 90.0,
                        "subnets": ["10.64.1.0/24"],
                    }
                ],
                "removed": [],
                "failed": [],
                "pool_probe": {"available": None},
            },
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_unused",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--docker-all", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"dry_run": True, "include_networks": True}
    assert "old_default" in result.output
    assert "10.64.1.0/24" in result.output


def test_docker_old_can_be_combined_with_explicit_network_flag(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=30, dry_run=False, include_networks=False):
        captured.update(days=days, include_networks=include_networks)
        return {
            "success": True,
            "command": "docker image prune -a --force --filter until=720h",
            "output": "",
            "estimated_max_gb": 0,
            "space_freed_gb": 0,
            "days": days,
            "network_cleanup": {
                "success": True,
                "min_age_days": 0,
                "candidates": [],
                "removed": [],
                "failed": [],
                "pool_probe": {"available": None},
            },
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_old_unused",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--docker-old", "--docker-networks", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"days": 30, "include_networks": True}


def test_planned_orphan_network_cleanup_uses_previewed_ids(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=0, dry_run=False, network_ids=None):
        captured.update(days=days, dry_run=dry_run, network_ids=network_ids)
        return {"success": True, "removed": [], "failed": []}

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_networks",
        fake_cleanup,
    )
    planned = {
        "cleanup_kind": "docker-networks",
        "details": {
            "orphan_networks": [
                {"id": "a" * 64, "name": "old_default"},
            ]
        },
    }

    result = cleanup_cmd._execute_planned_cleanup(object(), planned)

    assert result["success"] is True
    assert captured == {
        "days": 0,
        "dry_run": False,
        "network_ids": ["a" * 64],
    }


def test_welcome_menu_lists_docker_old_option():
    from fixos.cli.main import cli

    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    assert "fixos cleanup --docker-all" in result.output
    assert "unused images/cache i osierocone sieci" in result.output
    assert "fixos cleanup --docker-old" in result.output
    assert "stare obrazy/cache i osierocone sieci" in result.output
    assert "fixos cleanup --docker-networks" in result.output
    assert "pulę adresową" in result.output
    assert "fixos cleanup --ollama-old" in result.output
    assert "modele Ollama" in result.output


def test_docker_networks_flag_routes_to_safe_network_cleanup(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=0, dry_run=False):
        captured["days"] = days
        captured["dry_run"] = dry_run
        return {
            "success": True,
            "candidates": [
                {
                    "id": "a" * 64,
                    "short_id": "a" * 12,
                    "name": "old_default",
                    "age_days": 12.5,
                }
            ],
            "removed": [],
            "failed": [],
            "pool_probe": {"available": None, "error": "skipped in dry-run"},
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_networks",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--docker-networks", "--days", "7", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"days": 7, "dry_run": True}
    assert "old_default" in result.output
    assert "brak faktycznych zmian" in result.output


def test_docker_networks_alias_reports_successful_pool_probe(monkeypatch):
    def fake_cleanup(self, days=0, dry_run=False):
        return {
            "success": True,
            "candidates": [],
            "removed": [],
            "failed": [],
            "pool_probe": {"available": True, "removed": True, "error": ""},
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_docker_networks",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["-c", "docker-networks"],
    )

    assert result.exit_code == 0, result.output
    assert "Pula adresowa: dostępna" in result.output


def test_ollama_old_flag_defaults_to_90_days(monkeypatch):
    captured = {}

    def fake_cleanup(self, days=90, dry_run=False):
        captured["days"] = days
        captured["dry_run"] = dry_run
        return {
            "success": True,
            "command": "ollama rm old:7b",
            "output": "[DRY RUN] Would remove 1 model(s)",
            "estimated_max_gb": 4.7,
            "space_freed_gb": 4.7,
            "days": days,
            "models": [{"name": "old:7b", "size_gb": 4.7}],
            "skipped_running": [],
        }

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_ollama_old_unused",
        fake_cleanup,
    )

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--ollama-old", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"days": 90, "dry_run": True}
    assert "90" in result.output
    assert "ollama rm" in result.output


def test_safe_option_one_runs_ollama_old_age_action(monkeypatch):
    safe = _service("Npm", "safe")
    ollama_old = {
        "service_type": "ollama-old",
        "cleanup_kind": "ollama-old",
        "name": "Ollama (modele >90 dni)",
        "path": "",
        "size_mb": 4800,
        "size_gb": 4.7,
        "description": "old models",
        "can_cleanup": True,
        "cleanup_command": "ollama rm old:7b",
        "preview_command": "ollama list",
        "safe_to_cleanup": True,
        "risk_level": "safe",
        "details": {"days": 90},
        "days": 90,
    }
    plan = {
        "services": [ollama_old, safe],
        "safe_to_cleanup": [ollama_old, safe],
        "requires_review": [],
        "dangerous": [],
    }
    calls = []

    class Scanner:
        def cleanup_service(self, service_type, dry_run, planned_service):
            calls.append(("service", service_type))
            return {"success": True, "space_freed_gb": 1}

    def fake_ollama(self, days=90, dry_run=False):
        calls.append(("ollama-old", days, dry_run))
        return {"success": True, "space_freed_gb": 4.7}

    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "cleanup_ollama_old_unused",
        fake_ollama,
    )

    @click.command()
    def command():
        cleanup_cmd._run_interactive_cleanup(plan, False, Scanner())

    result = CliRunner().invoke(command, input="1\n")

    assert result.exit_code == 0, result.output
    assert "Ollama (modele >90 dni)" in result.output
    assert ("ollama-old", 90, False) in calls
    assert ("service", "npm") in calls
    assert "Zwolniono 4.70 GB" in result.output


def test_build_safe_age_actions_includes_old_ollama(monkeypatch):
    models = [
        {
            "name": "old:7b",
            "size_bytes": 5 * 1024**3,
            "modified_at": "2025-01-01T00:00:00+00:00",
        }
    ]
    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "list_ollama_models",
        staticmethod(lambda: models),
    )
    monkeypatch.setattr(
        cleanup_cmd.ServiceCleaner,
        "list_running_ollama_models",
        staticmethod(lambda: set()),
    )

    class Scanner:
        def scan_service(self, service_type):
            return []

    actions = cleanup_cmd.ServiceCleaner(Scanner()).build_safe_age_actions()
    kinds = [item["cleanup_kind"] for item in actions]
    assert "ollama-old" in kinds
    ollama = next(item for item in actions if item["cleanup_kind"] == "ollama-old")
    assert ollama["risk_level"] == "safe"
    assert ollama["safe_to_cleanup"] is True
    assert "old:7b" in ollama["cleanup_command"]
