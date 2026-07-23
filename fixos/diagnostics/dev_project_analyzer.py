"""
Dev Project Analyzer for FixOS - analyze developer project dependencies.

Wykrywa foldery zależności w prywatnych projektach użytkownika, które można
bezpiecznie usunąć i odtworzyć później:
- node_modules (npm/yarn/pnpm)
- venv, .venv (Python virtualenv)
- __pycache__ (Python cache)
- target (Maven/Gradle)
- build, dist (build artifacts)
- .tox, .pytest_cache (test cache)
- .mypy_cache (type checker cache)
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from fixos.diagnostics.utils import format_size as _format_size
from ..constants import (
    DEV_PROJECT_MAX_DEPTH,
    DEV_PROJECT_MIN_SIZE_MB,
    DEV_PROJECT_OLD_DAYS,
    FAST_COMMAND_TIMEOUT,
)


@dataclass
class ProjectDependency:
    """Represents a dependency folder that can be cleaned"""

    name: str
    path: str
    size_bytes: int
    dep_type: str  # node_modules, venv, target, etc.
    project_name: str
    last_modified: Optional[datetime]
    can_recreate: bool
    recreate_command: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "size_human": self._format_size(self.size_bytes),
            "dep_type": self.dep_type,
            "project_name": self.project_name,
            "last_modified": (
                self.last_modified.isoformat() if self.last_modified else None
            ),
            "days_since_modified": (
                (datetime.now() - self.last_modified).days
                if self.last_modified
                else None
            ),
            "can_recreate": self.can_recreate,
            "recreate_command": self.recreate_command,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        return _format_size(size_bytes)


class DevProjectAnalyzer:
    """
    Analyze developer projects for dependency folders that can be cleaned.

    Skanuje tylko prywatne projekty użytkownika w HOME.
    """

    # Dependency folder patterns with recreate commands
    DEP_PATTERNS = {
        # Node.js
        "node_modules": {
            "indicators": [
                "package.json",
                "package-lock.json",
                "yarn.lock",
                "pnpm-lock.yaml",
            ],
            "recreate": "npm install / yarn install / pnpm install",
            "priority": "high",  # Often very large
        },
        # Python
        "venv": {
            "indicators": [
                "pyvenv.cfg",
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
            ],
            "recreate": "python -m venv venv && pip install -r requirements.txt",
            "priority": "high",
        },
        ".venv": {
            "indicators": [
                "pyvenv.cfg",
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
            ],
            "recreate": "python -m venv .venv && pip install -r requirements.txt",
            "priority": "high",
        },
        "__pycache__": {
            "indicators": [],  # Always safe to remove
            "recreate": "Automatically recreated on next Python run",
            "priority": "low",
        },
        ".tox": {
            "indicators": ["tox.ini"],
            "recreate": "tox",
            "priority": "medium",
        },
        ".pytest_cache": {
            "indicators": ["pytest.ini", "pyproject.toml"],
            "recreate": "pytest (recreated on next run)",
            "priority": "low",
        },
        ".mypy_cache": {
            "indicators": ["mypy.ini", "pyproject.toml"],
            "recreate": "mypy (recreated on next run)",
            "priority": "low",
        },
        "build": {
            "indicators": ["setup.py", "pyproject.toml"],
            "recreate": "python -m build / pip wheel",
            "priority": "medium",
        },
        "dist": {
            "indicators": ["setup.py", "pyproject.toml"],
            "recreate": "python -m build",
            "priority": "medium",
        },
        "*.egg-info": {
            "indicators": ["setup.py", "pyproject.toml"],
            "recreate": "pip install -e .",
            "priority": "low",
        },
        # Java/JVM
        "target": {
            "indicators": [
                "Cargo.toml",
                "pom.xml",
                "build.gradle",
                "build.gradle.kts",
            ],
            "recreate": "cargo build / mvn install / gradle build",
            "recreate_by_indicator": {
                "Cargo.toml": "cargo build",
                "pom.xml": "mvn install",
                "build.gradle": "gradle build",
                "build.gradle.kts": "gradle build",
            },
            "priority": "high",
        },
        ".gradle": {
            "indicators": ["build.gradle", "build.gradle.kts"],
            "recreate": "gradle build (downloads dependencies)",
            "priority": "medium",
        },
        # Go / PHP
        "vendor": {
            "indicators": ["go.mod", "composer.json"],
            "recreate": "go mod vendor / composer install",
            "recreate_by_indicator": {
                "go.mod": "go mod vendor",
                "composer.json": "composer install",
            },
            "priority": "high",
        },
        # .NET
        "bin": {
            "indicators": ["*.csproj", "*.sln"],
            "recreate": "dotnet build",
            "priority": "medium",
        },
        "obj": {
            "indicators": ["*.csproj", "*.sln"],
            "recreate": "dotnet build",
            "priority": "low",
        },
        # Ruby
        "vendor/bundle": {
            "indicators": ["Gemfile", "Gemfile.lock"],
            "recreate": "bundle install",
            "priority": "high",
        },
    }

    def __init__(self, home_dir: Optional[str] = None):
        self.home_dir = Path(home_dir or os.path.expanduser("~"))
        self.dependencies: List[ProjectDependency] = []
        self.total_size = 0

    def analyze(self, max_depth: int = DEV_PROJECT_MAX_DEPTH) -> Dict[str, Any]:
        """
        Scan home directory for dependency folders.

        Args:
            max_depth: Maximum directory depth to scan
        """
        self.dependencies = []

        # Scan common project locations
        scan_paths = [
            self.home_dir / "projects",
            self.home_dir / "Projects",
            self.home_dir / "workspace",
            self.home_dir / "Workspace",
            self.home_dir / "code",
            self.home_dir / "Code",
            self.home_dir / "dev",
            self.home_dir / "Dev",
            self.home_dir / "src",
            self.home_dir / "github",
            self.home_dir / "gitlab",
            self.home_dir / "repos",
            self.home_dir,  # Also scan home directly
        ]

        for scan_path in scan_paths:
            if scan_path.exists() and scan_path.is_dir():
                self._scan_directory(scan_path, max_depth)

        # Sort by size
        self.dependencies.sort(key=lambda x: -x.size_bytes)

        # Calculate totals
        self.total_size = sum(dep.size_bytes for dep in self.dependencies)

        # Group by type
        by_type = {}
        for dep in self.dependencies:
            if dep.dep_type not in by_type:
                by_type[dep.dep_type] = []
            by_type[dep.dep_type].append(dep.to_dict())

        return {
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "by_type": by_type,
            "total_size": self.total_size,
            "total_size_human": ProjectDependency._format_size(self.total_size),
            "total_count": len(self.dependencies),
            "projects_affected": len(
                set(dep.project_name for dep in self.dependencies)
            ),
        }

    def _scan_directory(self, directory: Path, max_depth: int, current_depth: int = 0):
        """Recursively scan directory for dependency folders"""
        if current_depth > max_depth:
            return

        # Skip hidden directories and common exclusions
        skip_dirs = {".git", ".svn", ".hg", ".idea", ".vscode", ".vs"}

        try:
            for item in directory.iterdir():
                if not item.is_dir():
                    continue

                # Check if this is a dependency folder
                dep_info = self._check_dependency_folder(item)
                if dep_info:
                    self.dependencies.append(dep_info)
                    continue  # Don't scan inside dependency folders

                # Skip excluded directories
                if item.name in skip_dirs or item.name.startswith("."):
                    continue

                # Recurse into subdirectories
                self._scan_directory(item, max_depth, current_depth + 1)

        except PermissionError:
            pass
        except Exception:
            pass

    def _check_dependency_folder(self, folder: Path) -> Optional[ProjectDependency]:
        """Check if folder is a dependency folder and return info"""
        folder_name = folder.name

        # Check exact matches
        if folder_name in self.DEP_PATTERNS:
            pattern_info = self.DEP_PATTERNS[folder_name]
            return self._create_dependency(folder, folder_name, pattern_info)

        # Check glob patterns (e.g., *.egg-info)
        for pattern, pattern_info in self.DEP_PATTERNS.items():
            if "*" in pattern:
                # Simple glob matching
                import fnmatch

                if fnmatch.fnmatch(folder_name, pattern):
                    return self._create_dependency(folder, pattern, pattern_info)

        return None

    def _create_dependency(
        self, folder: Path, dep_type: str, pattern_info: dict
    ) -> ProjectDependency:
        """Create ProjectDependency object"""
        # Get size
        size_bytes = self._get_dir_size(folder)

        # Get last modified time
        try:
            last_modified = datetime.fromtimestamp(folder.stat().st_mtime)
        except Exception:
            last_modified = None

        # Get project name (parent directory)
        project_name = folder.parent.name
        if folder.parent.parent.name in ["projects", "Projects", "workspace", "code"]:
            project_name = folder.parent.name

        # Check if can recreate (has indicator files)
        can_recreate = self._check_can_recreate(
            folder, pattern_info.get("indicators", [])
        )
        recreate_command = pattern_info.get("recreate", "Unknown")
        for indicator, command in pattern_info.get("recreate_by_indicator", {}).items():
            if self._indicator_exists(folder.parent, indicator):
                recreate_command = command
                break

        return ProjectDependency(
            name=folder.name,
            path=str(folder),
            size_bytes=size_bytes,
            dep_type=dep_type,
            project_name=project_name,
            last_modified=last_modified,
            can_recreate=can_recreate,
            recreate_command=recreate_command,
        )

    def _get_dir_size(self, path: Path) -> int:
        """Get directory size using du"""
        try:
            result = subprocess.run(
                ["du", "-sb", str(path)],
                capture_output=True,
                text=True,
                timeout=FAST_COMMAND_TIMEOUT,
            )
            if result.returncode == 0:
                return int(result.stdout.split()[0])
        except Exception:
            pass
        return 0

    def _check_can_recreate(self, folder: Path, indicators: List[str]) -> bool:
        """Check if dependency can be recreated (has indicator files)"""
        if not indicators:
            return True  # Always safe (like __pycache__)

        parent = folder.parent
        return any(
            self._indicator_exists(parent, indicator) for indicator in indicators
        )

    @staticmethod
    def _indicator_exists(parent: Path, indicator: str) -> bool:
        """Match both literal marker files and simple glob indicators."""
        if any(token in indicator for token in ("*", "?", "[")):
            return any(parent.glob(indicator))
        return (parent / indicator).exists()

    def get_old_dependencies(
        self, days: int = DEV_PROJECT_OLD_DAYS
    ) -> List[ProjectDependency]:
        """Get dependencies not modified in X days"""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            dep
            for dep in self.dependencies
            if dep.last_modified and dep.last_modified < cutoff
        ]

    def get_large_dependencies(
        self, min_size_mb: int = DEV_PROJECT_MIN_SIZE_MB
    ) -> List[ProjectDependency]:
        """Get dependencies larger than X MB"""
        min_bytes = min_size_mb * 1024 * 1024
        return [dep for dep in self.dependencies if dep.size_bytes >= min_bytes]

    def get_summary(self) -> str:
        """Get human-readable summary"""
        analysis = self.analyze()

        lines = [
            "=" * 60,
            "📦 DEVELOPER PROJECT DEPENDENCIES",
            "=" * 60,
            "",
        ]

        if not self.dependencies:
            lines.append("✅ Brak folderów zależności do wyczyszczenia.")
            return "\n".join(lines)

        # Group by type
        by_type = {}
        for dep in self.dependencies:
            if dep.dep_type not in by_type:
                by_type[dep.dep_type] = []
            by_type[dep.dep_type].append(dep)

        for dep_type, deps in sorted(
            by_type.items(), key=lambda x: -sum(d.size_bytes for d in x[1])
        ):
            total = sum(d.size_bytes for d in deps)
            lines.append(
                f"\n{dep_type.upper()} ({ProjectDependency._format_size(total)})"
            )
            for dep in deps[:5]:
                days = ""
                if dep.last_modified:
                    days_old = (datetime.now() - dep.last_modified).days
                    if days_old > 30:
                        days = f" [{days_old}d old]"
                lines.append(
                    f"  • {dep.project_name}: {ProjectDependency._format_size(dep.size_bytes)}{days}"
                )
            if len(deps) > 5:
                lines.append(f"  ... i {len(deps) - 5} więcej")

        lines.append(f"\n{'=' * 60}")
        lines.append(f"💰 ŁĄCZNIE: {analysis['total_size_human']}")
        lines.append(f"📁 Projekty: {analysis['projects_affected']}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_cleanup_commands(self) -> List[Dict[str, Any]]:
        """Get cleanup commands for each dependency"""
        commands = []

        for dep in self.dependencies:
            commands.append(
                {
                    "description": f"Usuń {dep.dep_type} z {dep.project_name}",
                    "command": f"rm -rf {dep.path}",
                    "size": dep.size_bytes,
                    "size_human": ProjectDependency._format_size(dep.size_bytes),
                    "recreate": dep.recreate_command,
                    "safe": dep.can_recreate,
                }
            )

        return commands
