"""System-level storage analyzers (DNF, kernels, journal, orphaned, coredumps, snap, var_cache, logs)."""

from __future__ import annotations

import os
import re
import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fixos.diagnostics.storage_analyzer import StorageItem

from fixos.constants import (
    MIN_COREDUMP_MB,
    MIN_DEBUGINFO_MB,
    MIN_DNF_CACHE_MB,
    MIN_JOURNAL_LOG_MB,
    MIN_ORPHANED_PACKAGES,
)
from fixos.diagnostics.storage_analyzer import StorageItem

_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.:@%~-]*$")
_PACKAGE_OUTPUT_HEADINGS = {
    "available",
    "command",
    "dependencies",
    "error",
    "failed",
    "found",
    "installed",
    "last",
    "matches",
    "metadata",
    "n/a",
    "no",
    "nothing",
    "package",
    "removing",
    "warning",
}


def _observed_package_names(output: str, *, limit: int = 30) -> list[str]:
    """Extract bounded, literal package names from read-only command output."""
    names: list[str] = []
    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        candidate = stripped.split(maxsplit=1)[0] if stripped else ""
        if not candidate or candidate.lower().rstrip(":.,") in _PACKAGE_OUTPUT_HEADINGS:
            continue
        if _PACKAGE_NAME_RE.fullmatch(candidate) is None or candidate in names:
            continue
        names.append(candidate)
        if len(names) >= limit:
            break
    return names


def _exact_dnf_remove_command(package_names: list[str]) -> str:
    """Build a DNF command whose target set is fixed by the diagnostic scan."""
    return "sudo dnf remove -y -- " + " ".join(
        shlex.quote(package_name) for package_name in package_names
    )


class _SystemAnalyzerMixin:
    """Mixin providing system-level _analyze_* methods for StorageAnalyzer."""

    def _analyze_dnf_cache(self):
        """Analyze DNF package cache"""
        cache_paths = [
            "/var/cache/dnf",
        ]

        total_size = 0
        for path in cache_paths:
            if os.path.exists(path):
                size = self._get_dir_size(path)
                if size > MIN_DNF_CACHE_MB * 1024 * 1024:
                    total_size += size

        if total_size > MIN_DNF_CACHE_MB * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="DNF Cache",
                    path="/var/cache/dnf",
                    size_bytes=total_size,
                    category="packages",
                    risk="none",
                    cleanup_command="sudo dnf clean all",
                    description="Cache pobranych pakietów DNF - bezpieczne do usunięcia",
                )
            )

    def _analyze_old_kernels(self):
        """Analyze old kernel versions"""
        output = self._run_command(["rpm", "-q", "kernel"])
        if not output:
            return

        kernels = _observed_package_names(output)
        if len(kernels) <= 2:
            return  # Keep at least 2 kernels

        current = self._run_command(["uname", "-r"])
        if not current:
            return

        current_version = current.strip()
        old_kernels = [k for k in kernels if current_version not in k]

        if old_kernels:
            estimated_size = len(old_kernels) * 200 * 1024 * 1024

            self.items.append(
                StorageItem(
                    name=f"Stare kernele ({len(old_kernels)})",
                    path="/boot",
                    size_bytes=estimated_size,
                    category="packages",
                    risk="medium",
                    cleanup_command=_exact_dnf_remove_command(old_kernels),
                    description=f"Masz {len(kernels)} kerneli, używasz {current_version}. "
                    f"Kandydaci do usunięcia (po podglądzie): {', '.join(old_kernels)}.",
                )
            )

    def _analyze_journal_logs(self):
        """Analyze systemd journal logs"""
        output = self._run_command(["journalctl", "--disk-usage"])
        if not output:
            return

        match = re.search(r"take up (\d+\.?\d*[KMG]?)", output)
        if not match:
            return

        size_str = match.group(1)
        size_bytes = self._parse_size(size_str)

        if size_bytes > MIN_JOURNAL_LOG_MB * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Journal logs",
                    path="/var/log/journal",
                    size_bytes=size_bytes,
                    category="logs",
                    risk="low",
                    cleanup_command="sudo journalctl --vacuum-time=7d",
                    description=f"Logi systemowe zajmują {size_str}. "
                    "Bezpiecznie ogranicz do 7 dni.",
                )
            )

    def _analyze_coredumps(self):
        """Analyze systemd coredumps"""
        coredump_path = "/var/lib/systemd/coredump"
        if not os.path.exists(coredump_path):
            return

        size = self._get_dir_size(coredump_path)
        if size > MIN_COREDUMP_MB * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Coredumps",
                    path=coredump_path,
                    size_bytes=size,
                    category="system",
                    risk="none",
                    cleanup_command="sudo rm -rf /var/lib/systemd/coredump/*",
                    description=f"Coredumpy (crash dumps) zajmują {StorageItem._format_size(size)}. "
                    "Bezpieczne do usunięcia.",
                )
            )

    def _analyze_orphaned_packages(self):
        """Analyze orphaned packages and debug symbols"""
        output = self._run_command(["dnf", "repoquery", "--installed", "*debuginfo*"])
        if output and output.strip():
            debug_packages = _observed_package_names(output)
            estimated_size = len(debug_packages) * 500 * 1024 * 1024

            if debug_packages and estimated_size > MIN_DEBUGINFO_MB * 1024 * 1024:
                self.items.append(
                    StorageItem(
                        name=f"Debug symbols ({len(debug_packages)})",
                        path="/usr/lib/debug",
                        size_bytes=estimated_size,
                        category="packages",
                        risk="medium",
                        cleanup_command=_exact_dnf_remove_command(debug_packages),
                        description=f"Pakiety debuginfo zajmują ~{StorageItem._format_size(estimated_size)}. "
                        f"Dokładne cele (po podglądzie): {', '.join(debug_packages)}.",
                    )
                )

        output = self._run_command(["package-cleanup", "--leaves"])
        if output and output.strip():
            orphaned = _observed_package_names(output)
            if len(orphaned) > MIN_ORPHANED_PACKAGES:
                estimated_size = len(orphaned) * 50 * 1024 * 1024

                self.items.append(
                    StorageItem(
                        name=f"Orphaned packages ({len(orphaned)})",
                        path="/var/lib/rpm",
                        size_bytes=estimated_size,
                        category="packages",
                        risk="medium",
                        cleanup_command=_exact_dnf_remove_command(orphaned),
                        description=f"Osierocone pakiety (leaves): {len(orphaned)}. "
                        "Biblioteki nie wymagane przez żaden pakiet. "
                        f"Dokładne cele (po podglądzie): {', '.join(orphaned)}.",
                    )
                )

    def _analyze_system_logs(self):
        """Analyze /var/log beyond journal"""
        log_path = "/var/log"
        if not os.path.exists(log_path):
            return

        size = self._get_dir_size(log_path)
        journal_size = self._get_dir_size("/var/log/journal")
        other_logs = size - journal_size

        if other_logs > 500 * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Other System Logs",
                    path=log_path,
                    size_bytes=other_logs,
                    category="logs",
                    risk="low",
                    cleanup_command="sudo logrotate -f /etc/logrotate.conf",
                    description=f"Inne logi systemowe zajmują {StorageItem._format_size(other_logs)}.",
                )
            )

    def _analyze_var_cache(self):
        """Analyze /var/cache"""
        if not os.path.exists("/var/cache"):
            return

        size = self._get_dir_size("/var/cache")
        dnf_size = self._get_dir_size("/var/cache/dnf")
        other_size = size - dnf_size

        if other_size > 200 * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Inne cache systemowe",
                    path="/var/cache",
                    size_bytes=other_size,
                    category="system_cache",
                    risk="medium",
                    cleanup_command="sudo rm -rf /var/cache/*",
                    description=f"Cache systemowe (poza DNF) zajmują "
                    f"{StorageItem._format_size(other_size)}.",
                )
            )

    def _parse_snap_line(self, line: str) -> dict | None:
        """Parse a single line from 'snap list --all' output. Returns None if invalid."""
        parts = line.split()
        if len(parts) < 4:
            return None
        name, version, rev = parts[0], parts[1], parts[2]
        status = parts[3] if len(parts) > 3 else ""
        is_disabled = "disabled" in status.lower()
        snap_path = f"/var/lib/snapd/snaps/{name}_{rev}.snap"
        size = self._get_file_size(snap_path) if os.path.exists(snap_path) else 0
        return {
            "name": name,
            "version": version,
            "rev": rev,
            "size": size,
            "disabled": is_disabled,
        }

    def _add_snap_items(self, snap_packages: list, old_count: int) -> None:
        """Append StorageItems for old snap versions and active snap total."""
        if old_count > 0:
            estimated_size = old_count * 100 * 1024 * 1024
            self.items.append(
                StorageItem(
                    name=f"Stare wersje Snap ({old_count})",
                    path="/var/lib/snapd",
                    size_bytes=estimated_size,
                    category="packages",
                    risk="low",
                    cleanup_command="sudo snap set system refresh.retain=2",
                    description=f"Masz {old_count} starych wersji pakietów Snap. Ogranicz do 2 wersji.",
                )
            )
        if snap_packages:
            active = [p for p in snap_packages if not p["disabled"]]
            total_snap_size = sum(p["size"] for p in active)
            if total_snap_size > 500 * 1024 * 1024:
                self.items.append(
                    StorageItem(
                        name=f"Zainstalowane Snap ({len(active)})",
                        path="/var/lib/snapd/snaps",
                        size_bytes=total_snap_size,
                        category="packages",
                        risk="medium",
                        cleanup_command="snap:interactive",
                        description=f"Masz {len(snap_packages)} pakietów Snap. Użyj 'snap' w menu aby zarządzać.",
                    )
                )

    def _analyze_snap(self):
        """Analyze Snap packages - old versions and installed packages"""
        if not os.path.exists("/var/lib/snapd"):
            return

        output = self._run_command(["snap", "list", "--all"])
        if not output:
            return

        snap_packages = []
        old_count = 0
        for line in output.strip().split("\n")[1:]:
            pkg = self._parse_snap_line(line)
            if pkg:
                snap_packages.append(pkg)
                if pkg["disabled"]:
                    old_count += 1

        self.snap_packages = snap_packages
        self._add_snap_items(snap_packages, old_count)
