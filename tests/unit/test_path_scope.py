"""Lexical containment must stay conservative without walking every ancestor."""

import os
from pathlib import Path

import pytest

from fixos.diagnostics.venv_cleanup import _within


@pytest.mark.parametrize(
    ("path", "parent", "expected"),
    [
        ("/", "/", True),
        ("/repo", "/repo", True),
        ("/repo/.venv/bin/python", "/repo", True),
        ("/repo-old/file", "/repo", False),
        ("/repo", "/repo/child", False),
        ("/elsewhere/file", "/repo", False),
        ("repo/child", "repo", True),
        ("repo/child", ".", True),
        ("/repo/child", ".", False),
        ("repo/child", "/repo", False),
        ("/repo/../elsewhere", "/repo", True),
    ],
)
def test_existing_lexical_scope_boundaries(path, parent, expected):
    assert _within(Path(path), Path(parent)) is expected


def test_native_case_rules_are_preserved():
    assert _within(Path("REPO/child"), Path("repo")) is (os.name == "nt")


@pytest.mark.skipif(os.name == "nt", reason="POSIX double-root semantics")
def test_distinct_posix_anchors_remain_distinct():
    assert not _within(Path("//host/share/file"), Path("/host/share"))


def test_unrelated_deep_path_does_not_enumerate_ancestors():
    class NoAncestorWalk(type(Path())):
        @property
        def parents(self):
            raise AssertionError("Containment must not enumerate all ancestors")

    path = NoAncestorWalk("/unrelated/" + "/".join(["nested"] * 2048))

    assert not _within(path, Path("/home/tom/github/project"))
