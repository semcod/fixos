"""Exact, window-preserving control of JetBrains AI plugins and Qoder helpers."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable, Collection, Sequence
from pathlib import Path
from typing import Any

import psutil

from fixos.diagnostics.jetbrains_recovery import (
    JETBRAINS_PRODUCTS,
    is_main_jetbrains_process,
    jetbrains_product_marker,
)
from fixos.diagnostics.process_chains import ProcessRecord, collect_processes


AI_PLUGIN_IDS = ("com.intellij.ml.llm", "com.qoder")


class JetBrainsAiSafetyError(RuntimeError):
    """Raised when an AI-control target cannot be proven exact and safe."""


class JetBrainsAiControl:
    """Inspect or explicitly disable AI plugins and stop exact Qoder helpers."""

    def __init__(
        self,
        *,
        process_provider: Callable[[], Sequence[ProcessRecord]] | None = None,
        config_root: Path | None = None,
        identity_provider: Callable[[int], float | None] | None = None,
        rss_provider: Callable[[int], int] | None = None,
        terminator: Callable[[int], None] | None = None,
        alive_provider: Callable[[int, float], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._process_provider = process_provider or collect_processes
        self._config_root = config_root or Path.home() / ".config" / "JetBrains"
        self._identity_provider = identity_provider or self._identity
        self._rss_provider = rss_provider or self._rss
        self._terminator = terminator or self._terminate
        self._alive_provider = alive_provider or self._alive
        self._clock = clock
        self._sleeper = sleeper

    @staticmethod
    def _identity(pid: int) -> float | None:
        try:
            return psutil.Process(pid).create_time()
        except (psutil.Error, OSError):
            return None

    @staticmethod
    def _rss(pid: int) -> int:
        try:
            return int(psutil.Process(pid).memory_info().rss)
        except (psutil.Error, OSError):
            return 0

    @staticmethod
    def _terminate(pid: int) -> None:
        psutil.Process(pid).terminate()

    @staticmethod
    def _alive(pid: int, expected_create_time: float) -> bool:
        try:
            process = psutil.Process(pid)
            return (
                abs(process.create_time() - expected_create_time) < 0.001
                and process.is_running()
                and process.status() != psutil.STATUS_ZOMBIE
            )
        except psutil.AccessDenied:
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return False

    @staticmethod
    def _is_qoder_helper(
        process: ProcessRecord, by_pid: dict[int, ProcessRecord]
    ) -> bool:
        command = process.cmdline or (process.name,)
        if Path(command[0]).name.casefold() != "qoder":
            return False
        if len(command) < 2 or command[1].casefold() != "start":
            return False
        parent = by_pid.get(process.ppid)
        return parent is not None and is_main_jetbrains_process(parent)

    def find_qoder_helpers(
        self, records: Sequence[ProcessRecord] | None = None
    ) -> list[ProcessRecord]:
        snapshot = list(records) if records is not None else list(self._process_provider())
        by_pid = {process.pid: process for process in snapshot}
        return sorted(
            (
                process
                for process in snapshot
                if self._is_qoder_helper(process, by_pid)
            ),
            key=lambda process: process.pid,
        )

    @staticmethod
    def _validate_config_dir(config_dir: Path) -> Path:
        path = config_dir.expanduser().absolute()
        if path.parent.name != "JetBrains":
            raise JetBrainsAiSafetyError("config directory is not under JetBrains")
        if not any(path.name.startswith(prefix) for prefix in JETBRAINS_PRODUCTS.values()):
            raise JetBrainsAiSafetyError("config directory is not a JetBrains product")
        if not path.is_dir():
            raise JetBrainsAiSafetyError("JetBrains config directory does not exist")
        return path

    def find_config_dirs(
        self,
        records: Sequence[ProcessRecord] | None = None,
        explicit: Path | None = None,
    ) -> list[Path]:
        if explicit is not None:
            return [self._validate_config_dir(explicit)]
        snapshot = list(records) if records is not None else list(self._process_provider())
        prefixes = {
            JETBRAINS_PRODUCTS[marker]
            for process in snapshot
            if (marker := jetbrains_product_marker(process)) is not None
        }
        found: list[Path] = []
        for prefix in sorted(prefixes):
            candidates = [
                path
                for path in self._config_root.glob(f"{prefix}*")
                if path.is_dir()
            ]
            if candidates:
                found.append(max(candidates, key=lambda path: path.name))
        return found

    @staticmethod
    def _disabled_plugins(config_dir: Path) -> tuple[str, ...]:
        path = config_dir / "disabled_plugins.txt"
        try:
            return tuple(
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise JetBrainsAiSafetyError(
                f"cannot read disabled plugin configuration: {exc}"
            ) from exc

    def status(self, *, config_dir: Path | None = None) -> dict[str, Any]:
        snapshot = list(self._process_provider())
        helpers = self.find_qoder_helpers(snapshot)
        configs = self.find_config_dirs(snapshot, explicit=config_dir)
        return {
            "service": "jetbrains-ai-control",
            "read_only": True,
            "plugin_ids": list(AI_PLUGIN_IDS),
            "helpers": [
                {
                    "pid": helper.pid,
                    "ppid": helper.ppid,
                    "create_time": helper.create_time,
                    "command": list(helper.cmdline),
                    "rss_bytes": self._rss_provider(helper.pid),
                }
                for helper in helpers
            ],
            "configs": [
                {
                    "directory": str(path),
                    "disabled_plugins_file": str(path / "disabled_plugins.txt"),
                    "disabled": [
                        plugin
                        for plugin in AI_PLUGIN_IDS
                        if plugin in self._disabled_plugins(path)
                    ],
                }
                for path in configs
            ],
        }

    def disable_plugins(self, config_dir: Path, *, apply: bool) -> dict[str, Any]:
        directory = self._validate_config_dir(config_dir)
        path = directory / "disabled_plugins.txt"
        entries = list(self._disabled_plugins(directory))
        added = [plugin for plugin in AI_PLUGIN_IDS if plugin not in entries]
        if apply and added:
            self._atomic_write(path, [*entries, *added])
        return {
            "config_dir": str(directory),
            "plugin_ids": list(AI_PLUGIN_IDS),
            "added": added,
            "changed": bool(apply and added),
            "dry_run": not apply,
            "restart_required": bool(added) or apply,
        }

    @staticmethod
    def _atomic_write(path: Path, entries: Collection[str]) -> None:
        temporary: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                if path.exists():
                    os.chmod(temporary, path.stat().st_mode & 0o777)
                for entry in entries:
                    handle.write(f"{entry}\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            raise JetBrainsAiSafetyError(
                f"cannot update disabled plugin configuration: {exc}"
            ) from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def stop_qoder_helpers(
        self,
        identities: Collection[tuple[int, float]],
        *,
        apply: bool,
        grace_seconds: float = 5.0,
    ) -> dict[str, Any]:
        if grace_seconds < 0:
            raise ValueError("grace_seconds must be non-negative")
        fresh = {
            (helper.pid, helper.create_time): helper
            for helper in self.find_qoder_helpers()
        }
        stopped: list[int] = []
        failed: list[dict[str, Any]] = []
        selected: list[tuple[ProcessRecord, float]] = []
        for pid, create_time in sorted(set(identities)):
            helper = fresh.get((int(pid), float(create_time)))
            current_identity = self._identity_provider(int(pid))
            if (
                helper is None
                or current_identity is None
                or abs(current_identity - float(create_time)) >= 0.001
            ):
                failed.append({"pid": pid, "error": "helper identity is no longer exact"})
                continue
            selected.append((helper, float(create_time)))
        if apply:
            for helper, _ in selected:
                try:
                    self._terminator(helper.pid)
                except (OSError, psutil.Error) as exc:
                    failed.append({"pid": helper.pid, "error": str(exc)})
            deadline = self._clock() + grace_seconds
            pending = list(selected)
            while pending and self._clock() < deadline:
                pending = [
                    item
                    for item in pending
                    if self._alive_provider(item[0].pid, item[1])
                ]
                if pending:
                    self._sleeper(min(0.1, max(0.0, deadline - self._clock())))
            for helper, create_time in selected:
                if self._alive_provider(helper.pid, create_time):
                    failed.append(
                        {"pid": helper.pid, "error": "helper did not exit after TERM"}
                    )
                elif not any(item["pid"] == helper.pid for item in failed):
                    stopped.append(helper.pid)
        return {
            "dry_run": not apply,
            "selected": [helper.pid for helper, _ in selected],
            "stopped": stopped,
            "failed": failed,
            "success": not failed,
        }
