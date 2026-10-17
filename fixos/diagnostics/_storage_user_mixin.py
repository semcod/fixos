"""User-level storage analyzers (cache, browsers, flatpak, dev projects, home, btrfs)."""

from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Any

from fixos.diagnostics.storage_analyzer import StorageItem
from fixos.constants import (
    MIN_BROWSER_CACHE_MB,
    MIN_HOME_LARGE_FILE_MB,
    MIN_HOME_LARGE_DIR_MB,
)


class _UserAnalyzerMixin:
    """Mixin providing user-level _analyze_* methods for StorageAnalyzer."""

    def _analyze_user_cache(self):
        """Analyze user cache directories"""
        cache_paths = [
            ("~/.cache/pip", "Python pip cache"),
            ("~/.cache/npm", "npm cache"),
            ("~/.cache/yarn", "Yarn cache"),
            ("~/.cache/go-build", "Go build cache"),
            ("~/.cache/gradle", "Gradle cache"),
            ("~/.cargo/registry", "Cargo registry"),
        ]

        for path, name in cache_paths:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                size = self._get_dir_size(expanded)
                if size > 50 * 1024 * 1024:
                    self.items.append(
                        StorageItem(
                            name=name,
                            path=expanded,
                            size_bytes=size,
                            category="user_cache",
                            risk="low",
                            cleanup_command=f"rm -rf {expanded}",
                            description=f"{name} zajmuje {StorageItem._format_size(size)}.",
                        )
                    )

    def _analyze_browser_cache(self):
        """Analyze browser cache"""
        browsers = [
            ("~/.cache/google-chrome", "Google Chrome cache"),
            ("~/.cache/mozilla", "Firefox cache"),
            ("~/.cache/brave", "Brave cache"),
            ("~/.cache/microsoft-edge", "Edge cache"),
        ]

        for path, name in browsers:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                size = self._get_dir_size(expanded)
                if size > MIN_BROWSER_CACHE_MB * 1024 * 1024:
                    self.items.append(
                        StorageItem(
                            name=name,
                            path=expanded,
                            size_bytes=size,
                            category="browser_cache",
                            risk="low",
                            cleanup_command=f"rm -rf {expanded}",
                            description=f"{name} zajmuje {StorageItem._format_size(size)}. "
                            "Uwaga: wyczyści dane sesji.",
                        )
                    )

    def _analyze_btrfs_snapshots(self):
        """Analyze Btrfs snapshots (major space consumer on Fedora)"""
        output = self._run_command(["btrfs", "subvolume", "list", "/"])
        if not output:
            return

        output = self._run_command(["snapper", "list"])
        if not output:
            return

        lines = output.strip().split("\n")[1:]
        snapshot_count = len(lines)

        if snapshot_count > 5:
            estimated_size = snapshot_count * 500 * 1024 * 1024

            self.items.append(
                StorageItem(
                    name=f"Btrfs Snapshots ({snapshot_count})",
                    path="/.snapshots",
                    size_bytes=estimated_size,
                    category="snapshots",
                    risk="medium",
                    cleanup_command="sudo snapper delete <old-id>",
                    description=f"Masz {snapshot_count} snapshotów. "
                    "Możesz usunąć stare, ale zachowaj kilka ostatnich.",
                )
            )

    def _analyze_browser_profiles(self):
        """Analyze browser profile bloat (not just cache)"""
        firefox_path = os.path.expanduser("~/.mozilla/firefox")
        if os.path.exists(firefox_path):
            size = self._get_dir_size(firefox_path)
            if size > 500 * 1024 * 1024:
                self.items.append(
                    StorageItem(
                        name="Firefox Profile",
                        path=firefox_path,
                        size_bytes=size,
                        category="browser_data",
                        risk="medium",
                        cleanup_command="about:support → Clear Profile Data",
                        description=f"Profil Firefox zajmuje {StorageItem._format_size(size)}. "
                        "Możesz wyczyścić dane w przeglądarce.",
                    )
                )

        chrome_path = os.path.expanduser("~/.config/google-chrome")
        if os.path.exists(chrome_path):
            size = self._get_dir_size(chrome_path)
            if size > 500 * 1024 * 1024:
                self.items.append(
                    StorageItem(
                        name="Chrome Profile",
                        path=chrome_path,
                        size_bytes=size,
                        category="browser_data",
                        risk="medium",
                        cleanup_command="chrome://settings/clearBrowserData",
                        description=f"Profil Chrome zajmuje {StorageItem._format_size(size)}.",
                    )
                )

    def _analyze_flatpak_user_data(self):
        """Analyze Flatpak user app data (~/.var/app)"""
        var_app_path = os.path.expanduser("~/.var/app")
        if not os.path.exists(var_app_path):
            return

        total_size = self._get_dir_size(var_app_path)
        if total_size < 500 * 1024 * 1024:
            return

        app_sizes = []
        for app_dir in os.listdir(var_app_path):
            app_path = os.path.join(var_app_path, app_dir)
            if os.path.isdir(app_path):
                size = self._get_dir_size(app_path)
                if size > 50 * 1024 * 1024:
                    app_sizes.append((app_dir, size))

        if app_sizes:
            app_sizes.sort(key=lambda x: -x[1])
            largest = app_sizes[:5]

            self.items.append(
                StorageItem(
                    name=f"Flatpak App Data ({len(app_sizes)} apps)",
                    path=var_app_path,
                    size_bytes=total_size,
                    category="flatpak",
                    risk="low",
                    cleanup_command="rm -rf ~/.var/app/*/cache",
                    description=f"Dane aplikacji Flatpak: {StorageItem._format_size(total_size)}. "
                    f"Największe: {', '.join(f'{a} ({StorageItem._format_size(s)})' for a, s in largest[:3])}. "
                    "Możesz bezpiecznie usunąć cache.",
                )
            )

    def _analyze_ostree_repo(self):
        """Analyze OSTree repo (Flatpak backend) for hidden bloat"""
        repo_path = "/var/lib/flatpak/repo/objects"
        if not os.path.exists(repo_path):
            return

        size = self._get_dir_size(repo_path)
        if size > 10 * 1024**3:
            self.items.append(
                StorageItem(
                    name="OSTree Objects DB",
                    path=repo_path,
                    size_bytes=size,
                    category="flatpak",
                    risk="low",
                    cleanup_command="sudo ostree prune --repo=/var/lib/flatpak/repo --depth=0",
                    description=f"OSTree objects DB zajmuje {StorageItem._format_size(size)}. "
                    "Możesz bezpiecznie przeprowadzić głębokie prune.",
                )
            )

    def _analyze_dev_projects(self):
        """Analyze developer project dependencies (node_modules, venv, target, etc.)"""
        from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer

        try:
            dev_analyzer = DevProjectAnalyzer()
            analysis = dev_analyzer.analyze(max_depth=5)

            for dep in dev_analyzer.dependencies:
                risk = "low" if dep.can_recreate else "medium"

                self.items.append(
                    StorageItem(
                        name=f"{dep.dep_type} ({dep.project_name})",
                        path=dep.path,
                        size_bytes=dep.size_bytes,
                        category="dev_projects",
                        risk=risk,
                        cleanup_command=f"rm -rf {dep.path}",
                        description=f"{dep.dep_type} w projekcie {dep.project_name}: "
                        f"{StorageItem._format_size(dep.size_bytes)}. "
                        f"Odtworzenie: {dep.recreate_command}",
                    )
                )
        except Exception:
            pass

    def _analyze_home_directory(self):
        """Analyze home directory for large files and folders"""
        home_path = os.path.expanduser("~")
        if not os.path.exists(home_path):
            return

        large_files = self._find_large_files(
            home_path, min_size_mb=MIN_HOME_LARGE_FILE_MB
        )
        large_dirs = self._find_large_home_dirs(
            home_path, min_size_mb=MIN_HOME_LARGE_DIR_MB
        )

        self.home_large_files = large_files
        self.home_large_dirs = large_dirs

        if large_files or large_dirs:
            total_size = sum(f["size"] for f in large_files) + sum(
                d["size"] for d in large_dirs
            )
            self.items.append(
                StorageItem(
                    name=f"Duże pliki w home ({len(large_files) + len(large_dirs)})",
                    path=home_path,
                    size_bytes=total_size,
                    category="home_analysis",
                    risk="medium",
                    cleanup_command="home:interactive",
                    description=f"Znaleziono {len(large_files)} dużych plików i {len(large_dirs)} folderów. "
                    f"Użyj 'home' w menu aby zarządzać.",
                )
            )

    def _find_large_files(
        self, path: str, min_size_mb: int = MIN_HOME_LARGE_FILE_MB
    ) -> List[Dict[str, Any]]:
        """Find files larger than min_size_mb in path"""
        large_files = []
        min_size = min_size_mb * 1024 * 1024

        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".cache",
            ".local",
            ".config",
            ".cargo",
            ".rustup",
            "target",
            "build",
            "dist",
            ".tox",
        }

        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in skip_dirs]

                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        size = os.path.getsize(file_path)

                        if size > min_size:
                            large_files.append(
                                {
                                    "path": file_path,
                                    "size": size,
                                    "size_human": StorageItem._format_size(size),
                                    "type": "file",
                                }
                            )
                    except (OSError, PermissionError):
                        continue

                if len(large_files) > 100:
                    break
        except Exception:
            pass

        large_files.sort(key=lambda x: -x["size"])
        return large_files[:50]

    def _find_large_home_dirs(
        self, path: str, min_size_mb: int = MIN_HOME_LARGE_DIR_MB
    ) -> List[Dict[str, Any]]:
        """Find directories larger than min_size_mb in home"""
        large_dirs = []
        min_size = min_size_mb * 1024 * 1024

        skip_names = {".git", ".cache", ".local", ".config", ".cargo", ".rustup"}
        skip_paths = {os.path.expanduser("~/github"), os.path.expanduser("~/projects")}

        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in skip_names]

                if any(root.startswith(p) for p in skip_paths):
                    dirs[:] = []
                    continue

                for d in dirs:
                    try:
                        dir_path = os.path.join(root, d)

                        if any(item.path == dir_path for item in self.items):
                            continue

                        size = self._get_dir_size(dir_path)

                        if size > min_size:
                            large_dirs.append(
                                {
                                    "path": dir_path,
                                    "size": size,
                                    "size_human": StorageItem._format_size(size),
                                    "type": "directory",
                                }
                            )
                    except (OSError, PermissionError):
                        continue

                if len(large_dirs) > 50:
                    break
        except Exception:
            pass

        large_dirs.sort(key=lambda x: -x["size"])
        return large_dirs[:30]

    @staticmethod
    def _run_du_threshold(
        min_size_mb: int, scan_path: str
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["du", "-h", "--threshold", f"{min_size_mb}M", scan_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def get_large_directories(self, min_size_mb: int = 100) -> List[Dict[str, Any]]:
        """Find all directories larger than min_size_mb."""
        large_dirs = []

        scan_paths = ["/var", "/usr", "/opt", "/home", "/root"]

        for scan_path in scan_paths:
            if not os.path.exists(scan_path):
                continue

            try:
                result = self._run_du_threshold(min_size_mb, scan_path)

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        parts = line.split("\t")
                        if len(parts) == 2:
                            size_str, path = parts
                            size_bytes = self._parse_size(size_str)

                            if any(item.path == path for item in self.items):
                                continue

                            large_dirs.append(
                                {
                                    "path": path,
                                    "size": size_bytes,
                                    "size_human": StorageItem._format_size(size_bytes),
                                }
                            )
            except Exception:
                continue

        large_dirs.sort(key=lambda x: -x["size"])
        return large_dirs
