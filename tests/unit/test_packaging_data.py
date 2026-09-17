"""Regression guard: runtime YAML data must ship inside the fixos package.

Ticket-035 fixed a packaging gap where the wheel/sdist contained only
``*.py`` files, so a pip-installed fixos had no feature profiles, no
package catalog and no builtin profiles. These tests pin both halves of
the contract: the files exist next to the package and pyproject.toml
declares them as package data.
"""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

RUNTIME_DATA_FILES = [
    "features/data/packages.yaml",
    "features/data/profiles/developer.yaml",
    "features/data/profiles/office.yaml",
    "features/data/profiles/sysadmin.yaml",
    "profiles/desktop.yaml",
    "profiles/developer.yaml",
    "profiles/minimal.yaml",
    "profiles/server.yaml",
]

PACKAGE_DATA_PATTERNS = [
    "features/data/*.yaml",
    "features/data/profiles/*.yaml",
    "profiles/*.yaml",
]


class TestRuntimeDataFiles:
    def test_every_runtime_data_file_exists_in_package(self):
        missing = [
            rel
            for rel in RUNTIME_DATA_FILES
            if not (resources.files("fixos") / rel).is_file()
        ]
        assert missing == [], f"data files missing from fixos package: {missing}"

    def test_pyproject_declares_package_data(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        section = re.search(
            r"\[tool\.setuptools\.package-data\](.*?)(?=\n\[|\Z)",
            pyproject,
            flags=re.DOTALL,
        )
        assert section, "pyproject.toml is missing [tool.setuptools.package-data]"
        for pattern in PACKAGE_DATA_PATTERNS:
            assert pattern in section.group(1), (
                f"package-data does not cover {pattern!r}; installed wheels "
                "will silently drop runtime YAML data"
            )
