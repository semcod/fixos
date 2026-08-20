"""Persistent protection for intentionally retained orphan project workloads."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PIN_SCHEMA = "fixos.orphan-project-pins/v1"
PIN_FILENAME = "orphan-project-pins.json"


class OrphanProjectPinError(RuntimeError):
    """Raised when persistent pin state cannot be trusted."""


def normalize_project_path(value: str | os.PathLike[str]) -> str:
    """Return a stable absolute path without requiring the path to exist."""
    raw = os.fspath(value)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise ValueError("orphan project pin must be an absolute path")
    normalized = Path(os.path.normpath(str(candidate)))
    if normalized == Path("/"):
        raise ValueError("the filesystem root cannot be pinned")
    return str(normalized)


def default_pin_path() -> Path:
    """Return the XDG-compliant per-user pin store path."""
    config_root = Path(
        os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    ).expanduser()
    return config_root / "fixos" / PIN_FILENAME


class OrphanProjectPins:
    """Read and atomically update exact Compose working-directory pins."""

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else default_pin_path()
        self._now = now or (lambda: datetime.now(timezone.utc))

    def list(self) -> list[dict[str, str]]:
        """Load validated records, failing closed if the state is malformed."""
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OrphanProjectPinError(
                f"cannot read trusted orphan project pins from {self.path}: {exc}"
            ) from exc
        if not isinstance(payload, dict) or payload.get("schema") != PIN_SCHEMA:
            raise OrphanProjectPinError(
                f"invalid orphan project pin schema in {self.path}"
            )
        raw_records = payload.get("pins")
        if not isinstance(raw_records, list):
            raise OrphanProjectPinError(
                f"invalid orphan project pin list in {self.path}"
            )
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise OrphanProjectPinError(
                    f"invalid orphan project pin record in {self.path}"
                )
            try:
                normalized = normalize_project_path(str(raw["path"]))
                created_at = str(raw["created_at"])
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError) as exc:
                raise OrphanProjectPinError(
                    f"invalid orphan project pin record in {self.path}: {exc}"
                ) from exc
            if normalized in seen:
                raise OrphanProjectPinError(
                    f"duplicate orphan project pin in {self.path}: {normalized}"
                )
            seen.add(normalized)
            records.append({"path": normalized, "created_at": created_at})
        return sorted(records, key=lambda item: item["path"])

    def paths(self) -> tuple[str, ...]:
        """Return exact normalized paths used by the scanner."""
        return tuple(record["path"] for record in self.list())

    def pin(self, value: str | os.PathLike[str]) -> tuple[dict[str, str], bool]:
        """Persist one exact path and report whether state changed."""
        normalized = normalize_project_path(value)
        records = self.list()
        existing = next(
            (record for record in records if record["path"] == normalized), None
        )
        if existing is not None:
            return existing, False
        record = {
            "path": normalized,
            "created_at": self._now().astimezone(timezone.utc).isoformat(),
        }
        records.append(record)
        self._write(records)
        return record, True

    def unpin(self, value: str | os.PathLike[str]) -> bool:
        """Remove one exact path, leaving unrelated pins untouched."""
        normalized = normalize_project_path(value)
        records = self.list()
        remaining = [record for record in records if record["path"] != normalized]
        if len(remaining) == len(records):
            return False
        self._write(remaining)
        return True

    def _write(self, records: list[dict[str, str]]) -> None:
        payload: dict[str, Any] = {
            "schema": PIN_SCHEMA,
            "pins": sorted(records, key=lambda item: item["path"]),
        }
        temporary: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                os.chmod(temporary, 0o600)
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise OrphanProjectPinError(
                f"cannot persist orphan project pins to {self.path}: {exc}"
            ) from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
