"""Test direct module execution via python -m fixos and python -m fixos.cli."""

from __future__ import annotations

import subprocess
import sys


def test_python_m_fixos_version():
    """Verify python -m fixos --version runs successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "fixos", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "fixos" in result.stdout.lower() or "version" in result.stdout.lower()


def test_python_m_fixos_cli_version():
    """Verify python -m fixos.cli --version runs successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "fixos.cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "fixos" in result.stdout.lower() or "version" in result.stdout.lower()


def test_python_m_fixos_cli_help():
    """Verify python -m fixos.cli --help displays CLI options."""
    result = subprocess.run(
        [sys.executable, "-m", "fixos.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "python -m fixos.cli" in result.stdout or "fixos" in result.stdout
