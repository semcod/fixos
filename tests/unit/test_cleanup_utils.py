import click
from click.testing import CliRunner

from fixos.cli import _cleanup_flatpak
from fixos.cli._cleanup_utils import _parse_selection


def test_parse_selection_critical_uses_explicit_priorities():
    priorities = ["low", "critical", "HIGH", " Critical ", "medium"]

    assert _parse_selection(
        "critical", len(priorities), priorities=priorities
    ) == [1, 3]


def test_parse_selection_critical_without_priorities_fails_closed():
    assert _parse_selection("critical", 3) == []


def test_parse_selection_preserves_existing_explicit_modes():
    priorities = ["critical", "low", "critical"]

    assert _parse_selection("1,3", 3, priorities=priorities) == [0, 2]
    assert _parse_selection("all", 3, priorities=priorities) == [0, 1, 2]
    assert _parse_selection("none", 3, priorities=priorities) == []


def test_flatpak_flow_passes_recommendation_priorities(monkeypatch):
    recommendations = [
        {
            "priority": "critical",
            "risk": "low",
            "description": "critical action",
            "action": "flatpak uninstall --unused",
            "estimated_savings": "1 MB",
        },
        {
            "priority": "low",
            "risk": "none",
            "description": "low action",
            "action": "true",
            "estimated_savings": "0 B",
        },
    ]
    captured = {}

    class Analyzer:
        def analyze(self):
            return {}

        def get_cleanup_recommendations(self):
            return recommendations

    def capture(selection, max_count, *, priorities=None):
        captured.update(
            selection=selection,
            max_count=max_count,
            priorities=priorities,
        )
        return []

    monkeypatch.setattr(
        "fixos.diagnostics.flatpak_analyzer.FlatpakAnalyzer", Analyzer
    )
    monkeypatch.setattr(_cleanup_flatpak, "_display_flatpak_status", lambda analysis: None)
    monkeypatch.setattr(_cleanup_flatpak, "_parse_selection", capture)

    @click.command()
    def command():
        _cleanup_flatpak._cleanup_flatpak_detailed(None, False, True)

    result = CliRunner().invoke(command, input="critical\n")

    assert result.exit_code == 0, result.output
    assert captured == {
        "selection": "critical",
        "max_count": 2,
        "priorities": ["critical", "low"],
    }
