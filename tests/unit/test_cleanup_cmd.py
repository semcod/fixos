import click
from click.testing import CliRunner

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
