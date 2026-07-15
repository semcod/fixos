"""Testy jednostkowe dla interaktywnego wyboru w `fixos projects`."""

from __future__ import annotations

import click

from fixos.cli import projects_cmd as pc
from fixos.diagnostics.project_scanner import ProjectArtifact


def _artifact(
    project_name="repo",
    project_path="/x/repo",
    artifact_name="venv",
    ecosystem="python",
    size_mb=1024.0,
    stale=False,
    days=1,
) -> ProjectArtifact:
    return ProjectArtifact(
        project_name=project_name,
        project_path=project_path,
        artifact_name=artifact_name,
        artifact_path=f"{project_path}/{artifact_name}",
        size_mb=size_mb,
        size_gb=round(size_mb / 1024, 3),
        description="",
        ecosystem=ecosystem,
        risk_level="safe",
        days_since_modified=days,
        stale=stale,
        cleanup_command=f"rm -rf {project_path}/{artifact_name}",
    )


class TestShortProjectPath:
    def test_shows_last_two_components(self):
        assert pc._short_project_path("/home/tom/github/semcod/fixOS") == "semcod/fixOS"

    def test_falls_back_to_full_path_when_too_short(self):
        assert pc._short_project_path("/repo") == "/repo"


class TestGroupBy:
    def test_groups_by_ecosystem(self):
        a1 = _artifact(ecosystem="python")
        a2 = _artifact(ecosystem="node", artifact_name="node_modules")
        a3 = _artifact(ecosystem="python", project_name="other", project_path="/x/other")

        groups = pc._group_by([a1, a2, a3], lambda a: a.ecosystem)

        assert set(groups) == {"python", "node"}
        assert groups["python"] == [a1, a3]
        assert groups["node"] == [a2]

    def test_groups_by_project(self):
        a1 = _artifact(project_path="/x/a")
        a2 = _artifact(project_path="/x/b")

        groups = pc._group_by([a1, a2], lambda a: a.project_path)

        assert groups == {"/x/a": [a1], "/x/b": [a2]}


class TestPickFromGroups:
    def test_all_selects_everything(self, monkeypatch):
        groups = {"python": [_artifact()], "node": [_artifact(ecosystem="node")]}
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "all")

        selected = pc._pick_from_groups(groups)

        assert len(selected) == 2

    def test_specific_indices(self, monkeypatch):
        big = _artifact(size_mb=2000)
        small = _artifact(size_mb=100, project_path="/x/small")
        groups = {"big": [big], "small": [small]}
        # Sorted by size descending -> [1] big, [2] small
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "1")

        selected = pc._pick_from_groups(groups)

        assert selected == [big]

    def test_multiple_indices_comma_separated(self, monkeypatch):
        a = _artifact(size_mb=2000, project_path="/x/a")
        b = _artifact(size_mb=1000, project_path="/x/b")
        c = _artifact(size_mb=500, project_path="/x/c")
        groups = {"a": [a], "b": [b], "c": [c]}
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "1, 3")

        selected = pc._pick_from_groups(groups)

        assert selected == [a, c]

    def test_empty_input_selects_nothing(self, monkeypatch):
        groups = {"python": [_artifact()]}
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "")

        assert pc._pick_from_groups(groups) == []

    def test_out_of_range_index_is_ignored(self, monkeypatch):
        groups = {"python": [_artifact()]}
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "99")

        assert pc._pick_from_groups(groups) == []


class TestSelectArtifacts:
    def test_choice_0_cancels(self, monkeypatch):
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "0")
        assert pc._select_artifacts([_artifact()]) == []

    def test_choice_1_selects_all(self, monkeypatch):
        artifacts = [_artifact(), _artifact(project_path="/x/b")]
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "1")

        assert pc._select_artifacts(artifacts) == artifacts

    def test_choice_2_selects_only_stale(self, monkeypatch):
        stale = _artifact(stale=True, project_path="/x/stale")
        fresh = _artifact(stale=False, project_path="/x/fresh")
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "2")

        assert pc._select_artifacts([stale, fresh]) == [stale]

    def test_stale_option_absent_from_prompt_when_nothing_stale(self, monkeypatch):
        captured = {}

        def fake_prompt(*args, **kwargs):
            captured["choices"] = kwargs.get("type").choices
            return "1"

        monkeypatch.setattr(click, "prompt", fake_prompt)

        pc._select_artifacts([_artifact(stale=False)])

        assert "2" not in captured["choices"]

    def test_choice_3_delegates_to_ecosystem_grouping(self, monkeypatch):
        artifacts = [_artifact(ecosystem="python")]
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "3")
        called = {}
        monkeypatch.setattr(
            pc, "_pick_from_groups", lambda groups, **k: called.setdefault("groups", groups)
        )

        pc._select_artifacts(artifacts)

        assert set(called["groups"]) == {"python"}

    def test_choice_4_delegates_to_project_grouping(self, monkeypatch):
        artifacts = [_artifact(project_path="/x/repo")]
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "4")
        called = {}
        monkeypatch.setattr(
            pc, "_pick_from_groups", lambda groups, **k: called.setdefault("groups", groups)
        )

        pc._select_artifacts(artifacts)

        assert set(called["groups"]) == {"/x/repo"}

    def test_choice_5_asks_per_item(self, monkeypatch):
        a1 = _artifact(project_path="/x/a")
        a2 = _artifact(project_path="/x/b")
        monkeypatch.setattr(click, "prompt", lambda *a, **k: "5")
        # Alternate confirm answers by call order: keep the first, skip the second.
        answers = iter([True, False])
        monkeypatch.setattr(click, "confirm", lambda label: next(answers))

        selected = pc._select_artifacts([a1, a2])

        assert selected == [a1]
