"""Fast, local system snapshot used before the full fixOS analysis.

The quick path deliberately avoids LLM calls and recursive scans of ``/`` or
the whole home directory.  It measures a small allow-list of rebuildable
caches, records resource counters and compares them with earlier snapshots.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import psutil

HISTORY_SCHEMA = "fixos-quick-history-v1"
MAX_HISTORY_ITEMS = 192


@dataclass(frozen=True)
class CacheRule:
    id: str
    label: str
    paths: tuple[str, ...]
    command: str
    risk: str = "safe"
    stack: str | None = None


# Only explicit, rebuildable locations belong in the safe total.  Broad
# application-data directories (Docker, models, editor extensions, Trash)
# are intentionally absent.
CACHE_RULES: tuple[CacheRule, ...] = (
    CacheRule(
        "pip",
        "pip cache",
        ("~/.cache/pip", "~/Library/Caches/pip", "~/AppData/Local/pip/Cache"),
        "python -m pip cache purge",
        stack="python",
    ),
    CacheRule(
        "uv",
        "uv cache",
        ("~/.cache/uv", "~/Library/Caches/uv", "~/AppData/Local/uv/cache"),
        "uv cache clean",
        stack="python",
    ),
    CacheRule(
        "npm",
        "npm cache",
        (
            "~/.npm/_cacache",
            "~/.npm/_npx",
            "~/.npm/_prebuilds",
            "~/AppData/Local/npm-cache/_cacache",
            "~/AppData/Local/npm-cache/_npx",
        ),
        (
            "npm cache clean --force 2>/dev/null || true; "
            "rm -rf ~/.npm/_npx ~/.npm/_prebuilds"
        ),
        stack="node",
    ),
    CacheRule(
        "pnpm",
        "pnpm store",
        ("~/.local/share/pnpm/store", "~/.pnpm-store"),
        "pnpm store prune",
        stack="node",
    ),
    CacheRule(
        "yarn", "Yarn cache", ("~/.cache/yarn",), "yarn cache clean", stack="node"
    ),
    CacheRule(
        "conda",
        "Conda package cache",
        ("~/miniconda3/pkgs", "~/anaconda3/pkgs", "~/.conda/pkgs"),
        "conda clean --all",
        stack="python",
    ),
    CacheRule(
        "poetry",
        "Poetry cache",
        ("~/.cache/pypoetry/cache", "~/.cache/pypoetry/artifacts"),
        "poetry cache clear --all pypi",
        stack="python",
    ),
    CacheRule(
        "chrome",
        "Chrome cache",
        (
            "~/.cache/google-chrome",
            "~/Library/Caches/Google/Chrome",
            "~/AppData/Local/Google/Chrome/User Data/Default/Cache",
        ),
        "rm -rf ~/.cache/google-chrome/*",
        stack="desktop",
    ),
    CacheRule(
        "firefox",
        "Firefox cache",
        (
            "~/.cache/mozilla",
            "~/Library/Caches/Firefox",
            "~/AppData/Local/Mozilla/Firefox/Profiles",
        ),
        "rm -rf ~/.cache/mozilla/*",
        stack="desktop",
    ),
    CacheRule(
        "thumbnails",
        "Thumbnail cache",
        ("~/.cache/thumbnails", "~/.thumbnails"),
        "rm -rf ~/.cache/thumbnails/* ~/.thumbnails/*",
        stack="desktop",
    ),
    CacheRule(
        "shader",
        "GPU shader cache",
        ("~/.cache/mesa_shader_cache", "~/.nv/ComputeCache"),
        "rm -rf ~/.cache/mesa_shader_cache/* ~/.nv/ComputeCache/*",
        stack="desktop",
    ),
    CacheRule(
        "ccache",
        "Compiler cache",
        ("~/.ccache", "~/.cache/sccache"),
        "ccache --clear 2>/dev/null || true; rm -rf ~/.cache/sccache/*",
        stack="developer",
    ),
    CacheRule(
        "apt",
        "APT package cache",
        ("/var/cache/apt/archives",),
        "sudo apt-get clean",
    ),
    CacheRule(
        "playwright",
        "Playwright browsers",
        ("~/.cache/ms-playwright", "~/.cache/puppeteer"),
        "rm -rf ~/.cache/ms-playwright ~/.cache/puppeteer",
        risk="review",
        stack="node",
    ),
    CacheRule(
        "jetbrains",
        "JetBrains indexes/cache",
        ("~/.cache/JetBrains",),
        "review in fixos cleanup --list",
        risk="review",
        stack="developer",
    ),
)


def _state_dir(override: str | Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    configured = os.environ.get("FIXOS_STATE_DIR")
    if configured:
        return Path(configured)
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / "fixos"
    return Path.home() / ".local" / "state" / "fixos"


def _docker_cache_path() -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "fixos" / "docker-usage.json"


def _read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for raw in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            values[key] = value.strip().strip('"')
    except OSError:
        pass
    return values


def _detect_context(cwd: Path) -> dict[str, Any]:
    os_release = _read_os_release()
    command_stacks = {
        "docker": ("docker", "podman"),
        "python": ("python3", "uv", "conda", "poetry"),
        "node": ("node", "npm", "pnpm", "yarn"),
        "java": ("java", "gradle", "mvn"),
        "rust": ("cargo", "rustc"),
        "go": ("go",),
        "mobile": ("flutter", "adb"),
        "local-ai": ("ollama",),
    }
    stacks = [
        name
        for name, commands in command_stacks.items()
        if any(shutil.which(command) for command in commands)
    ]

    marker_stacks = {
        "python": ("pyproject.toml", "requirements.txt", "setup.py"),
        "node": ("package.json", "pnpm-lock.yaml", "package-lock.json"),
        "rust": ("Cargo.toml",),
        "go": ("go.mod",),
        "java": ("pom.xml", "build.gradle", "build.gradle.kts"),
        "docker": ("Dockerfile", "compose.yaml", "docker-compose.yml"),
    }
    project_stacks = [
        name
        for name, markers in marker_stacks.items()
        if any((cwd / marker).exists() for marker in markers)
    ]
    stacks = sorted(set(stacks + project_stacks))

    home = Path.home()
    patterns = []
    if any((home / item).exists() for item in ("github", "Projects", ".gitconfig")):
        patterns.append("developer")
    if any(
        (home / item).exists()
        for item in (".ollama", ".lmstudio", ".cache/huggingface")
    ):
        patterns.append("local-ai")
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        patterns.append("desktop")
    if "docker" in stacks:
        patterns.append("containers")

    if "developer" in patterns or len(project_stacks) >= 1:
        profile = "developer"
    elif "desktop" in patterns:
        profile = "desktop"
    else:
        profile = "server"

    package_manager = next(
        (
            name
            for name in ("apt", "dnf", "pacman", "zypper", "brew")
            if shutil.which(name)
        ),
        "unknown",
    )
    return {
        "os": platform.system(),
        "release": platform.release(),
        "distribution": os_release.get("PRETTY_NAME", platform.platform()),
        "package_manager": package_manager,
        "profile": profile,
        "tech_stack": stacks,
        "project_stack": project_stacks,
        "user_patterns": sorted(set(patterns)),
        "cwd": str(cwd),
    }


def _du_kib(path: Path, timeout: float) -> tuple[int | None, str | None]:
    if not shutil.which("du"):
        return _walk_kib(path, timeout)
    try:
        result = subprocess.run(
            ["du", "-sk", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.splitlines()[-1].split()[0]), None
        return None, (result.stderr.strip() or f"du exit {result.returncode}")
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except (OSError, ValueError, IndexError) as exc:
        return None, str(exc)


def _walk_kib(path: Path, timeout: float) -> tuple[int | None, str | None]:
    """Portable bounded fallback for systems without the ``du`` utility."""
    deadline = time.monotonic() + timeout
    total = 0
    try:
        pending = [path]
        while pending:
            if time.monotonic() >= deadline:
                return None, "timeout"
            current = pending.pop()
            if current.is_symlink():
                continue
            if current.is_file():
                total += current.stat().st_size
                continue
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        return (total + 1023) // 1024, None
    except OSError as exc:
        return None, str(exc)


def _expand_existing(paths: Iterable[str], home: Path) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = (
            Path(raw.replace("~", str(home), 1)) if raw.startswith("~") else Path(raw)
        )
        if path.exists() and path not in seen:
            result.append(path)
            seen.add(path)
    return result


def _measure_caches(
    home: Path, timeout: float = 1.5
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    jobs: list[tuple[CacheRule, Path]] = []
    for rule in CACHE_RULES:
        jobs.extend((rule, path) for path in _expand_existing(rule.paths, home))

    measured: dict[str, list[tuple[Path, int]]] = {}
    errors: dict[str, list[str]] = {}
    if jobs:
        workers = min(10, len(jobs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_du_kib, path, timeout): (rule, path) for rule, path in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                rule, path = futures[future]
                kib, error = future.result()
                if kib is not None:
                    measured.setdefault(rule.id, []).append((path, kib))
                elif error:
                    errors.setdefault(rule.id, []).append(f"{path}: {error}")

    safe: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for rule in CACHE_RULES:
        rows = measured.get(rule.id, [])
        if not rows and rule.id not in errors:
            continue
        size_bytes = sum(kib for _, kib in rows) * 1024
        item = {
            "id": rule.id,
            "label": rule.label,
            "size_bytes": size_bytes,
            "size_gb": round(size_bytes / 1024**3, 3),
            "paths": [str(path) for path, _ in rows],
            "command": rule.command,
            "risk": rule.risk,
            "complete": rule.id not in errors,
        }
        if errors.get(rule.id):
            item["measurement_errors"] = errors[rule.id]
        (safe if rule.risk == "safe" else review).append(item)

    safe.sort(key=lambda item: item["size_bytes"], reverse=True)
    review.sort(key=lambda item: item["size_bytes"], reverse=True)
    return safe, review, not errors


def _cached_docker_review(
    now: datetime, max_age_hours: int = 24
) -> dict[str, Any] | None:
    path = _docker_cache_path()
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        recorded = datetime.fromisoformat(cached["generated_at"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if recorded.tzinfo is None:
        recorded = recorded.astimezone()
    age = now.astimezone() - recorded.astimezone()
    if age > timedelta(hours=max_age_hours):
        return None
    usage = cached.get("usage", cached)
    rows = usage.get("rows", {})
    build = rows.get("Build Cache") or rows.get("Build cache")
    if not build:
        return None
    reclaimable = float(build.get("reclaimable_mb", 0)) * 1024**2
    return {
        "id": "docker-build-cache",
        "label": "Docker build cache (dane z ostatniego pełnego skanu)",
        "size_bytes": int(reclaimable),
        "size_gb": round(reclaimable / 1024**3, 3),
        "paths": ["/var/lib/docker"],
        "command": "docker builder prune --filter until=168h",
        "risk": "review",
        "complete": True,
        "cache_age_minutes": round(age.total_seconds() / 60, 1),
    }


def _sample_process_load(
    logical_cpus: int, *, interval: float = 0.12
) -> tuple[float, list[dict[str, Any]]]:
    """Sample system and per-process CPU over the same bounded interval."""
    sampled_processes: list[psutil.Process] = []
    for process in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            process.cpu_percent(interval=None)
            sampled_processes.append(process)
        except (psutil.Error, OSError):
            continue

    system_cpu_percent = psutil.cpu_percent(interval=interval)
    processes: list[dict[str, Any]] = []
    for process in sampled_processes:
        try:
            info = process.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name") or "?",
                    "memory_percent": round(float(info.get("memory_percent") or 0), 1),
                    "cpu_percent": round(float(process.cpu_percent(interval=None)), 1),
                }
            )
        except (psutil.Error, OSError):
            continue

    processes.sort(
        key=lambda row: (
            max(row["cpu_percent"] / logical_cpus, row["memory_percent"]),
            row["cpu_percent"],
            row["memory_percent"],
        ),
        reverse=True,
    )
    return system_cpu_percent, processes[:5]


def _resource_snapshot() -> dict[str, Any]:
    logical_cpus = psutil.cpu_count() or 1
    cpu_percent, processes = _sample_process_load(logical_cpus)
    try:
        load_1, load_5, load_15 = os.getloadavg()
    except (AttributeError, OSError):
        load_1 = load_5 = load_15 = 0.0
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk_mount = Path.home().anchor or "/"
    disk = psutil.disk_usage(disk_mount)

    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "logical_cpus": logical_cpus,
            "load": [round(load_1, 2), round(load_5, 2), round(load_15, 2)],
            "load_1_normalized_percent": round(load_1 / logical_cpus * 100, 1),
        },
        "memory": {
            "total_bytes": memory.total,
            "used_bytes": memory.used,
            "available_bytes": memory.available,
            "percent": memory.percent,
        },
        "swap": {
            "total_bytes": swap.total,
            "used_bytes": swap.used,
            "percent": swap.percent,
        },
        "disk": {
            "mount": disk_mount,
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent": disk.percent,
        },
        "top_processes": processes,
    }


def _load_history(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != HISTORY_SCHEMA:
            return []
        return [row for row in payload.get("snapshots", []) if isinstance(row, dict)]
    except (OSError, TypeError, json.JSONDecodeError):
        return []


def _write_history(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": HISTORY_SCHEMA, "snapshots": rows[-MAX_HISTORY_ITEMS:]}
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            tmp_name = handle.name
        os.replace(tmp_name, path)
    finally:
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass


def _history_row(
    generated_at: str,
    resources: dict[str, Any],
    safe_items: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "disk_used_bytes": resources["disk"]["used_bytes"],
        "disk_percent": resources["disk"]["percent"],
        "memory_used_bytes": resources["memory"]["used_bytes"],
        "memory_percent": resources["memory"]["percent"],
        "swap_used_bytes": resources["swap"]["used_bytes"],
        "cpu_percent": resources["cpu"]["percent"],
        "load_1_normalized_percent": resources["cpu"]["load_1_normalized_percent"],
        "cache_sizes": {
            item["id"]: item["size_bytes"] for item in safe_items + review_items
        },
        "cache_complete": {
            item["id"]: item.get("complete", True) for item in safe_items + review_items
        },
    }


def _parse_timestamp(row: dict[str, Any]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(row["generated_at"]))
        return parsed if parsed.tzinfo else parsed.astimezone()
    except (KeyError, TypeError, ValueError):
        return None


def _delta(current: int | float, base: int | float) -> int | float:
    return current - base


def _growth_report(
    history: list[dict[str, Any]], current: dict[str, Any], now: datetime, hours: int
) -> dict[str, Any]:
    valid = [(stamp, row) for row in history if (stamp := _parse_timestamp(row))]
    if not valid:
        return {
            "status": "baseline_created",
            "message": "Utworzono punkt odniesienia; przyrost będzie widoczny przy następnym uruchomieniu.",
            "window_hours": hours,
            "escalating": [],
            "cache_growth": [],
        }

    valid.sort(key=lambda pair: pair[0])
    cutoff = now - timedelta(hours=hours)
    recent = [pair for pair in valid if pair[0] >= cutoff]
    base_time, base = recent[0] if recent else valid[-1]
    elapsed_hours = max((now - base_time).total_seconds() / 3600, 1 / 3600)
    disk_delta = int(_delta(current["disk_used_bytes"], base.get("disk_used_bytes", 0)))
    memory_delta = int(
        _delta(current["memory_used_bytes"], base.get("memory_used_bytes", 0))
    )
    swap_delta = int(_delta(current["swap_used_bytes"], base.get("swap_used_bytes", 0)))

    cache_growth = []
    old_caches = base.get("cache_sizes", {})
    old_cache_complete = base.get("cache_complete", {})
    current_cache_complete = current.get("cache_complete", {})
    for cache_id, size in current.get("cache_sizes", {}).items():
        if (
            cache_id not in old_caches
            or not old_cache_complete.get(cache_id, False)
            or not current_cache_complete.get(cache_id, False)
        ):
            continue
        change = int(size - old_caches.get(cache_id, 0))
        if change > 0:
            cache_growth.append({"id": cache_id, "delta_bytes": change})
    cache_growth.sort(key=lambda row: row["delta_bytes"], reverse=True)

    escalating = []
    disk_rate = disk_delta / elapsed_hours
    if disk_delta >= 1024**3 and (
        disk_rate >= 512 * 1024**2 or current["disk_percent"] >= 90
    ):
        escalating.append(
            {
                "resource": "disk",
                "severity": "critical" if current["disk_percent"] >= 95 else "warning",
                "delta_bytes": disk_delta,
                "rate_bytes_per_hour": int(disk_rate),
            }
        )
    if current["memory_percent"] >= 90 and memory_delta > 0:
        escalating.append(
            {
                "resource": "memory",
                "severity": "critical",
                "delta_bytes": memory_delta,
            }
        )
    if current["cpu_percent"] >= 90 or current["load_1_normalized_percent"] >= 100:
        escalating.append(
            {
                "resource": "cpu",
                "severity": "warning",
                "current_percent": current["cpu_percent"],
                "load_percent": current["load_1_normalized_percent"],
            }
        )

    today_rows = [
        pair for pair in valid if pair[0].astimezone().date() == now.astimezone().date()
    ]
    today: dict[str, Any]
    if today_rows:
        today_time, today_base = today_rows[0]
        today_cache_growth = []
        today_old_caches = today_base.get("cache_sizes", {})
        today_old_complete = today_base.get("cache_complete", {})
        for cache_id, size in current.get("cache_sizes", {}).items():
            if (
                cache_id not in today_old_caches
                or not today_old_complete.get(cache_id, False)
                or not current_cache_complete.get(cache_id, False)
            ):
                continue
            change = int(size - today_old_caches.get(cache_id, 0))
            if change > 0:
                today_cache_growth.append({"id": cache_id, "delta_bytes": change})
        today_cache_growth.sort(key=lambda row: row["delta_bytes"], reverse=True)
        today = {
            "status": "compared",
            "since": today_time.isoformat(),
            "disk_delta_bytes": int(
                _delta(current["disk_used_bytes"], today_base.get("disk_used_bytes", 0))
            ),
            "memory_delta_bytes": int(
                _delta(
                    current["memory_used_bytes"],
                    today_base.get("memory_used_bytes", 0),
                )
            ),
            "cache_growth": today_cache_growth[:8],
        }
    else:
        today = {"status": "no_baseline_today"}

    return {
        "status": "compared",
        "since": base_time.isoformat(),
        "elapsed_hours": round(elapsed_hours, 2),
        "window_hours": hours,
        "disk_delta_bytes": disk_delta,
        "disk_rate_bytes_per_hour": int(disk_rate),
        "memory_delta_bytes": memory_delta,
        "swap_delta_bytes": swap_delta,
        "cache_growth": cache_growth[:8],
        "escalating": escalating,
        "today": today,
    }


def _profile_thresholds(profile_name: str) -> dict[str, int | float]:
    defaults: dict[str, int | float] = {
        "disk_usage_warning": 85,
        "disk_usage_critical": 95,
        "memory_usage_warning": 80,
        "memory_usage_critical": 90,
        "swap_usage_warning": 75,
        "cpu_usage_warning": 90,
    }
    try:
        from fixos.profiles import Profile

        defaults.update(Profile.load(profile_name).thresholds)
    except (FileNotFoundError, OSError, TypeError, ValueError):
        pass
    return defaults


def _alerts(
    resources: dict[str, Any],
    growth: dict[str, Any],
    thresholds: dict[str, int | float],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    disk = resources["disk"]
    memory = resources["memory"]
    swap = resources["swap"]
    cpu = resources["cpu"]
    disk_critical = thresholds["disk_usage_critical"]
    disk_warning = thresholds["disk_usage_warning"]
    memory_warning = thresholds["memory_usage_warning"]
    memory_critical = thresholds["memory_usage_critical"]
    swap_warning = thresholds["swap_usage_warning"]
    cpu_warning = thresholds["cpu_usage_warning"]
    if disk["percent"] >= disk_critical:
        alerts.append(
            {
                "resource": "disk",
                "severity": "critical",
                "message": (
                    "Dysk systemowy przekroczył próg krytyczny "
                    f"{disk_critical:.0f}%."
                ),
            }
        )
    elif disk["percent"] >= disk_warning:
        alerts.append(
            {
                "resource": "disk",
                "severity": "warning",
                "message": (
                    f"Dysk systemowy przekroczył próg profilu {disk_warning:.0f}%."
                ),
            }
        )
    if memory["percent"] >= memory_critical:
        alerts.append(
            {
                "resource": "memory",
                "severity": "critical",
                "message": f"Zajętość RAM przekroczyła {memory_critical:.0f}%.",
            }
        )
    elif memory["percent"] >= memory_warning:
        alerts.append(
            {
                "resource": "memory",
                "severity": "warning",
                "message": f"Zajętość RAM przekroczyła {memory_warning:.0f}%.",
            }
        )
    if swap["total_bytes"] and swap["percent"] >= swap_warning:
        alerts.append(
            {
                "resource": "swap",
                "severity": "warning",
                "message": f"Swap przekroczył {swap_warning:.0f}% zajętości.",
            }
        )
    if cpu["percent"] >= cpu_warning or cpu["load_1_normalized_percent"] >= 100:
        alerts.append(
            {
                "resource": "cpu",
                "severity": "warning",
                "message": "Wykryto wysokie chwilowe obciążenie CPU.",
            }
        )
    for escalation in growth.get("escalating", []):
        resource = escalation["resource"]
        if not any(item["resource"] == resource for item in alerts):
            alerts.append(
                {
                    "resource": resource,
                    "severity": escalation["severity"],
                    "message": f"Wykryto szybki wzrost użycia zasobu: {resource}.",
                }
            )
    return alerts


def collect_quick_snapshot(
    *,
    hours: int = 6,
    save: bool = True,
    state_dir: str | Path | None = None,
    home: str | Path | None = None,
    cwd: str | Path | None = None,
    cache_timeout: float = 1.5,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Collect a bounded, heuristic snapshot without using an LLM."""
    started = time.monotonic()
    now = now or datetime.now().astimezone()
    home_path = Path(home) if home is not None else Path.home()
    cwd_path = Path(cwd) if cwd is not None else Path.cwd()
    generated_at = now.isoformat()

    resources = _resource_snapshot()
    context = _detect_context(cwd_path)
    thresholds = _profile_thresholds(context.get("profile", "desktop"))
    context["thresholds"] = thresholds
    safe_items, review_items, measurement_complete = _measure_caches(
        home_path, timeout=cache_timeout
    )
    docker_review = _cached_docker_review(now)
    if docker_review:
        review_items.append(docker_review)
        review_items.sort(key=lambda item: item["size_bytes"], reverse=True)

    history_path = _state_dir(state_dir) / "quick-history.json"
    history = _load_history(history_path)
    current_row = _history_row(generated_at, resources, safe_items, review_items)
    growth = _growth_report(history, current_row, now, max(1, hours))
    alerts = _alerts(resources, growth, thresholds)

    if save:
        _write_history(history_path, history + [current_row])

    safe_total = sum(item["size_bytes"] for item in safe_items)
    return {
        "$schema": "fixos-quick-snapshot-v1",
        "generated_at": generated_at,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "mode": "heuristic-local",
        "context": context,
        "resources": resources,
        "safe_reclaim": {
            "estimated_max_bytes": safe_total,
            "estimated_max_gb": round(safe_total / 1024**3, 3),
            "measurement_complete": measurement_complete,
            "items": safe_items,
        },
        "review": review_items,
        "growth": growth,
        "alerts": alerts,
        "history_path": str(history_path),
        "deep_analysis": {
            "available": True,
            "command": "fixos quick --deep",
            "message": "Analiza głęboka jest opcjonalna i nie jest potrzebna do szybkiego wyniku.",
        },
    }
