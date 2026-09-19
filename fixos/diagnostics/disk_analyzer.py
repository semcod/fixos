#!/usr/bin/env python3
# ruff: noqa: EXE001,I001,UP035,RUF013,UP006,DTZ005,BLE001,RUF010,S110,RUF012,DTZ006
"""
Disk Analyzer Module for fixOS
Analyzes disk usage and groups cleanup causes
"""

import os
import shlex
import shutil
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from ..constants import (
    DISK_USAGE_CRITICAL,
    DISK_USAGE_WARNING,
    DISK_USAGE_MODERATE,
    MAX_LARGE_FILES_DEFAULT,
    MAX_CACHE_DIRS_DEFAULT,
    MAX_LOG_DIRS_DEFAULT,
    MAX_TEMP_DIRS_DEFAULT,
    MIN_FILE_SIZE_MB,
    LARGE_FILE_SIZE_MB,
    CACHE_SIZE_HIGH_MB,
    CACHE_SIZE_MEDIUM_MB,
)


class DiskAnalyzer:
    """Analyzes disk usage and provides cleanup suggestions"""

    def __init__(self, base_path: str = "/"):
        self.base_path = Path(base_path)
        self.cache_patterns = [
            ".cache",
            "__pycache__",
            "node_modules",
            ".npm",
            ".pip",
            "cache",
            "Cache",
            ".gradle",
            ".maven",
            ".cargo",
            "apt",
            "dnf",
            "yum",
            "pacman",
            "pkg",
            "docker/overlay2",
            "docker/image",
            "Containers",
        ]
        self.log_patterns = [".log", "logs", "Logs", "*.log", "*.out", "*.err"]
        self.temp_patterns = ["tmp", "temp", ".tmp", "Temp", "/tmp", "/var/tmp"]

    def analyze_disk_usage(self, path: str = None) -> Dict[str, Any]:
        """Comprehensive disk usage analysis"""
        if path is None:
            path = str(self.base_path)

        path = Path(path)
        if not path.exists():
            return {"error": f"Path {path} does not exist"}

        try:
            stat = shutil.disk_usage(path)
            total_gb = stat.total / (1024**3)
            used_gb = stat.used / (1024**3)
            free_gb = stat.free / (1024**3)
            usage_percent = (used_gb / total_gb) * 100

            large_files = self.get_large_files(path)
            cache_dirs = self.get_cache_dirs(path)
            log_dirs = self.get_log_dirs(path)
            temp_dirs = self.get_temp_dirs(path)

            analysis = {
                "path": str(path),
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 2),
                "status": self._get_disk_status(usage_percent),
                "large_files": large_files,
                "cache_dirs": cache_dirs,
                "log_dirs": log_dirs,
                "temp_dirs": temp_dirs,
                "suggestions": self.suggest_cleanup_actions(
                    path,
                    large_files=large_files,
                    cache_dirs=cache_dirs,
                    log_dirs=log_dirs,
                    temp_dirs=temp_dirs,
                ),
                "timestamp": datetime.now().isoformat(),
            }

            return analysis

        except Exception as e:
            return {"error": f"Failed to analyze {path}: {str(e)}"}

    def _get_disk_status(self, usage_percent: float) -> str:
        """Get disk status based on usage percentage"""
        if usage_percent >= DISK_USAGE_CRITICAL:
            return "critical"
        elif usage_percent >= DISK_USAGE_WARNING:
            return "warning"
        elif usage_percent >= DISK_USAGE_MODERATE:
            return "moderate"
        else:
            return "healthy"

    def get_large_files(
        self,
        path: Path,
        min_size_mb: int = MIN_FILE_SIZE_MB,
        max_files: int = MAX_LARGE_FILES_DEFAULT,
    ) -> List[Dict]:
        """Find large files using os.walk to avoid rglob memory explosion."""
        large_files = []

        try:
            for dirpath, _dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    try:
                        st = file_path.stat()
                        size_mb = st.st_size / (1024**2)
                        if size_mb >= min_size_mb:
                            large_files.append(
                                {
                                    "path": str(file_path),
                                    "size_mb": round(size_mb, 2),
                                    "size_gb": round(size_mb / 1024, 3),
                                    "modified": datetime.fromtimestamp(
                                        st.st_mtime
                                    ).isoformat(),
                                    "category": self._categorize_file(file_path),
                                }
                            )
                            if len(large_files) >= max_files:
                                break
                    except (OSError, PermissionError):
                        continue
                if len(large_files) >= max_files:
                    break

        except Exception:
            pass

        # Sort by size (largest first)
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        return large_files[:max_files]

    def get_cache_dirs(
        self, path: Path, max_dirs: int = MAX_CACHE_DIRS_DEFAULT
    ) -> List[Dict]:
        """Find cache directories using os.walk to avoid rglob memory explosion."""
        cache_dirs = []

        try:
            for dirpath, dirnames, _filenames in os.walk(path):
                dir_path = Path(dirpath)
                dir_name = dir_path.name.lower()
                if any(pattern in dir_name for pattern in self.cache_patterns):
                    try:
                        size_mb = self._get_dir_size_mb(dir_path)
                        if size_mb > 10:  # Only include significant cache dirs
                            cache_dirs.append(
                                {
                                    "path": str(dir_path),
                                    "size_mb": round(size_mb, 2),
                                    "size_gb": round(size_mb / 1024, 3),
                                    "files_count": self._count_files_fast(
                                        dir_path
                                    ),
                                    "cache_type": self._identify_cache_type(
                                        dir_path
                                    ),
                                }
                            )
                    except (OSError, PermissionError):
                        continue
                    # Don't recurse into found cache dirs
                    dirnames.clear()

                if len(cache_dirs) >= max_dirs:
                    break

        except Exception:
            pass

        cache_dirs.sort(key=lambda x: x["size_mb"], reverse=True)
        return cache_dirs

    def get_log_dirs(
        self, path: Path, max_dirs: int = MAX_LOG_DIRS_DEFAULT
    ) -> List[Dict]:
        """Find log directories using os.walk to avoid rglob memory explosion."""
        log_dirs = []

        try:
            for dirpath, dirnames, _filenames in os.walk(path):
                dir_path = Path(dirpath)
                dir_name = dir_path.name.lower()
                if any(pattern in dir_name for pattern in ["log", "logs"]):
                    try:
                        size_mb = self._get_dir_size_mb(dir_path)
                        if size_mb > 5:  # Only include significant log dirs
                            log_dirs.append(
                                {
                                    "path": str(dir_path),
                                    "size_mb": round(size_mb, 2),
                                    "size_gb": round(size_mb / 1024, 3),
                                    "oldest_log": self._get_oldest_file_date(
                                        dir_path
                                    ),
                                    "newest_log": self._get_newest_file_date(
                                        dir_path
                                    ),
                                }
                            )
                    except (OSError, PermissionError):
                        continue
                    # Don't recurse into found log dirs
                    dirnames.clear()

                if len(log_dirs) >= max_dirs:
                    break

        except Exception:
            pass

        log_dirs.sort(key=lambda x: x["size_mb"], reverse=True)
        return log_dirs

    def get_temp_dirs(
        self, path: Path, max_dirs: int = MAX_TEMP_DIRS_DEFAULT
    ) -> List[Dict]:
        """Find temporary directories using os.walk to avoid rglob memory explosion."""
        temp_dirs = []

        try:
            for dirpath, dirnames, _filenames in os.walk(path):
                dir_path = Path(dirpath)
                dir_name = dir_path.name.lower()
                if any(pattern in dir_name for pattern in self.temp_patterns):
                    try:
                        size_mb = self._get_dir_size_mb(dir_path)
                        if size_mb > 5:
                            temp_dirs.append(
                                {
                                    "path": str(dir_path),
                                    "size_mb": round(size_mb, 2),
                                    "size_gb": round(size_mb / 1024, 3),
                                    "temp_type": self._identify_temp_type(dir_path),
                                }
                            )
                    except (OSError, PermissionError):
                        continue
                    # Don't recurse into found temp dirs
                    dirnames.clear()

                if len(temp_dirs) >= max_dirs:
                    break

        except Exception:
            pass

        temp_dirs.sort(key=lambda x: x["size_mb"], reverse=True)
        return temp_dirs

    def suggest_cleanup_actions(
        self,
        path: Path,
        *,
        large_files: List[Dict] | None = None,
        cache_dirs: List[Dict] | None = None,
        log_dirs: List[Dict] | None = None,
        temp_dirs: List[Dict] | None = None,
    ) -> List[Dict]:
        """Generate cleanup suggestions using heuristics.

        Accepts optional pre-scanned data to avoid redundant filesystem scans.
        Falls back to scanning if data is not provided (backward compat).
        """
        suggestions = []

        try:
            # Reuse pre-scanned data when available; scan only if needed.
            if large_files is None:
                large_files = self.get_large_files(
                    path, min_size_mb=LARGE_FILE_SIZE_MB, max_files=10
                )
            if cache_dirs is None:
                cache_dirs = self.get_cache_dirs(path, max_dirs=MAX_LOG_DIRS_DEFAULT)
            if log_dirs is None:
                log_dirs = self.get_log_dirs(path, max_dirs=8)
            if temp_dirs is None:
                temp_dirs = self.get_temp_dirs(path, max_dirs=8)

            # Cache cleanup suggestions
            for cache in cache_dirs[:5]:
                if cache["size_mb"] > CACHE_SIZE_MEDIUM_MB:
                    suggestions.append(
                        {
                            "type": "cache_cleanup",
                            "priority": "high"
                            if cache["size_mb"] > CACHE_SIZE_HIGH_MB
                            else "medium",
                            "path": cache["path"],
                            "size_gb": cache["size_gb"],
                            "description": f"Clear {cache['cache_type']} cache",
                            "command": (
                                f"{'sudo ' if cache.get('is_system') else ''}"
                                f"find -- {shlex.quote(cache['path'])} -xdev "
                                "-mindepth 1 -mtime +7 -delete"
                            ),
                            "preview_command": f"ls -la -- {shlex.quote(cache['path'])} 2>/dev/null",
                            "safe": cache["cache_type"]
                            in ["npm", "pip", "gradle", "maven"],
                            "impact": "high",
                        }
                    )

            # Log cleanup suggestions
            for log_dir in log_dirs[:3]:
                if log_dir["size_mb"] > 50:
                    suggestions.append(
                        {
                            "type": "log_cleanup",
                            "priority": "medium",
                            "path": log_dir["path"],
                            "size_gb": log_dir["size_gb"],
                            "description": "Clean old log files",
                            "command": (
                                f"{'sudo ' if log_dir.get('is_system') else ''}"
                                f"find -- {shlex.quote(log_dir['path'])} -xdev "
                                "-type f -name '*.log' -mtime +30 -delete"
                            ),
                            "preview_command": f"find -- {shlex.quote(log_dir['path'])} -xdev -type f -name '*.log' -mtime +30 2>/dev/null",
                            "safe": True,
                            "impact": "medium",
                        }
                    )

            # Docker and Package Manager specific suggestions
            # These are generated regardless if we found them in cache dirs to guarantee they are surfaced
            suggestions.append(
                {
                    "type": "docker_cleanup",
                    "priority": "high",
                    "path": "/var/lib/docker",
                    "size_gb": 0.0,  # Will be recalculated by planner
                    "description": "Clean unused Docker images and build cache (without volumes)",
                    "command": "docker image prune -af && docker builder prune -af",
                    "safe": False,
                    "impact": "high",
                }
            )

            suggestions.append(
                {
                    "type": "package_cleanup",
                    "priority": "medium",
                    "path": "/var/cache",
                    "size_gb": 0.0,  # Will be recalculated
                    "description": "Clean system package manager cache (apt/dnf/pacman)",
                    "command": "apt-get clean || dnf clean all || pacman -Scc --noconfirm",
                    "safe": True,
                    "impact": "medium",
                }
            )

            # Temp directory cleanup
            for temp_dir in temp_dirs[:3]:
                if temp_dir["size_mb"] > 20:
                    suggestions.append(
                        {
                            "type": "temp_cleanup",
                            "priority": "high",
                            "path": temp_dir["path"],
                            "size_gb": temp_dir["size_gb"],
                            "description": f"Clean {temp_dir['temp_type']} temporary files",
                            "command": (
                                f"{'sudo ' if temp_dir.get('is_system') else ''}"
                                f"find -- {shlex.quote(temp_dir['path'])} -xdev "
                                "-mindepth 1 -mtime +7 -delete"
                            ),
                            "preview_command": f"find -- {shlex.quote(temp_dir['path'])} -xdev -mindepth 1 -mtime +7 2>/dev/null",
                            "safe": temp_dir["temp_type"]
                            in ["system_temp", "app_temp"],
                            "impact": "medium",
                        }
                    )

            # Large file suggestions
            for file_info in large_files[:3]:
                if file_info["size_gb"] > 1.0:
                    suggestions.append(
                        {
                            "type": "large_file",
                            "priority": "low",
                            "path": file_info["path"],
                            "size_gb": file_info["size_gb"],
                            "description": f"Review large {file_info['category']} file",
                            "command": f"# Manual review needed: {file_info['path']}",
                            "safe": False,
                            "impact": "low",
                        }
                    )

        except Exception as e:
            suggestions.append(
                {
                    "type": "error",
                    "priority": "low",
                    "description": f"Could not generate suggestions: {str(e)}",
                    "safe": True,
                    "impact": "none",
                }
            )

        # Sort by priority and impact
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(
            key=lambda x: (
                priority_order.get(x.get("priority", "low"), 1),
                x.get("size_gb", 0),
            ),
            reverse=True,
        )

        return suggestions[:15]  # Limit to top 15 suggestions

    def _get_dir_size_mb(self, dir_path: Path) -> float:
        """Calculate directory size in MB using du to avoid rglob memory usage."""
        try:
            result = subprocess.run(
                ["du", "-sb", str(dir_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.split()[0]) / (1024**2)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        # Fallback: quick estimate from first-level entries only
        total_size = 0
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        return total_size / (1024**2)

    @staticmethod
    def _count_files_fast(dir_path: Path, limit: int = 100_000) -> int | str:
        """Count files without materializing a list in memory.

        Returns an integer count, or 'many' if counting exceeds the limit
        or the subprocess times out.
        """
        try:
            result = subprocess.run(
                ["find", str(dir_path), "-type", "f"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                count = result.stdout.count("\n")
                return count if count < limit else "many"
        except (subprocess.TimeoutExpired, OSError):
            pass
        return "many"

    def _categorize_file(self, file_path: Path) -> str:
        """Categorize file type"""
        ext = file_path.suffix.lower()
        name = file_path.name.lower()

        if ext in [".mp4", ".avi", ".mkv", ".mov", ".wmv"]:
            return "video"
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
            return "image"
        elif ext in [".zip", ".tar", ".gz", ".rar", ".7z"]:
            return "archive"
        elif ext in [".db", ".sqlite", ".sqlite3"]:
            return "database"
        elif "docker" in name:
            return "docker"
        elif "vm" in name or ext in [".vdi", ".vmdk", ".qcow2"]:
            return "virtual_machine"
        elif ext in [".iso", ".dmg"]:
            return "disk_image"
        else:
            return "other"

    _CACHE_TYPE_RULES: list[tuple[list[str], str]] = [
        (["npm", "node_modules"], "npm"),
        (["pip", "python"], "pip"),
        (["gradle"], "gradle"),
        (["maven"], "maven"),
        (["cargo"], "cargo"),
        (["docker", "containers"], "docker"),
        (["apt", "dnf", "yum", "pacman"], "package_manager"),
        (["browser", "chrome", "firefox"], "browser"),
    ]

    def _identify_cache_type(self, dir_path: Path) -> str:
        """Identify cache directory type"""
        name = dir_path.name.lower()
        path_str = str(dir_path).lower()
        combined = name + " " + path_str
        for keywords, cache_type in self._CACHE_TYPE_RULES:
            if any(kw in combined for kw in keywords):
                return cache_type
        return "application"

    def _identify_temp_type(self, dir_path: Path) -> str:
        """Identify temporary directory type"""
        path_str = str(dir_path)

        if "/tmp" in path_str or "/var/tmp" in path_str:
            return "system_temp"
        elif "temp" in path_str.lower():
            return "app_temp"
        else:
            return "unknown"

    def _get_oldest_file_date(self, dir_path: Path) -> str:
        """Get oldest file date in directory"""
        oldest_time = None
        try:
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    if oldest_time is None or mtime < oldest_time:
                        oldest_time = mtime
            if oldest_time:
                return datetime.fromtimestamp(oldest_time).isoformat()
        except Exception:
            pass
        return "unknown"

    def _get_newest_file_date(self, dir_path: Path) -> str:
        """Get newest file date in directory"""
        newest_time = None
        try:
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    if newest_time is None or mtime > newest_time:
                        newest_time = mtime
            if newest_time:
                return datetime.fromtimestamp(newest_time).isoformat()
        except Exception:
            pass
        return "unknown"


def main():
    """Test the disk analyzer"""
    analyzer = DiskAnalyzer()
    result = analyzer.analyze_disk_usage()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
