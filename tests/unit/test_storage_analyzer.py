"""Regression tests for exact package cleanup targets in storage analysis."""

from fixos.diagnostics.storage_analyzer import StorageAnalyzer
from fixos.diagnostics._storage_system_mixin import (
    _exact_dnf_remove_command,
    _observed_package_names,
)


def test_observed_package_names_drops_headings_and_shell_input():
    output = """Installed Packages
curl
bad; rm -rf /
openssl-libs
No matches found.
"""

    assert _observed_package_names(output) == ["curl", "openssl-libs"]


def test_exact_dnf_remove_command_has_fixed_targets():
    command = _exact_dnf_remove_command(["curl", "openssl-libs"])

    assert command == "sudo dnf remove -y -- curl openssl-libs"
    assert "$((" not in command
    assert "$ (" not in command
    assert "*" not in command


def test_old_kernel_cleanup_uses_observed_kernel_names(monkeypatch):
    analyzer = StorageAnalyzer()

    def run(command):
        if command == ["rpm", "-q", "kernel"]:
            return "kernel-6.6.1\nkernel-6.6.2\nkernel-6.6.3\n"
        if command == ["uname", "-r"]:
            return "6.6.3"
        raise AssertionError(command)

    monkeypatch.setattr(analyzer, "_run_command", run)
    analyzer._analyze_old_kernels()

    assert len(analyzer.items) == 1
    item = analyzer.items[0]
    assert item.cleanup_command == "sudo dnf remove -y -- kernel-6.6.1 kernel-6.6.2"
    assert item.risk == "medium"
    assert "--oldinstallonly" not in item.cleanup_command
    assert "6.6.3" not in item.cleanup_command


def test_orphan_and_debuginfo_cleanup_use_exact_observed_names(monkeypatch):
    analyzer = StorageAnalyzer()
    debug = "libfoo-debuginfo\nlibbar-debuginfo\n"
    orphaned = "\n".join(f"orphan-{index}" for index in range(6))

    def run(command):
        if command[:3] == ["dnf", "repoquery", "--installed"]:
            return debug
        if command == ["package-cleanup", "--leaves"]:
            return orphaned
        raise AssertionError(command)

    monkeypatch.setattr(analyzer, "_run_command", run)
    analyzer._analyze_orphaned_packages()

    commands = [item.cleanup_command for item in analyzer.items]
    assert commands == [
        "sudo dnf remove -y -- libfoo-debuginfo libbar-debuginfo",
        "sudo dnf remove -y -- " + " ".join(f"orphan-{index}" for index in range(6)),
    ]
    assert all(item.risk == "medium" for item in analyzer.items)
    assert all("$(" not in command and "*" not in command for command in commands)
