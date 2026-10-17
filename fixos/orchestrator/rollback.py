"""
Rollback system for fixOS — tracks executed operations and allows undoing them.

Each fix session generates a rollback log in ~/.fixos/rollback/.
Log contains (command, rollback_command) pairs for each executed operation.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class RollbackEntry:
    """Single recorded operation with its rollback command."""

    timestamp: str
    command: str
    rollback_command: Optional[str]
    stdout: str
    stderr: str
    success: bool
    exit_code: int


@dataclass
class RollbackSession:
    """A session of recorded operations that can be rolled back."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    entries: list[RollbackEntry] = field(default_factory=list)

    LOG_DIR = Path.home() / ".fixos" / "rollback"

    def record(
        self,
        command: str,
        rollback_cmd: Optional[str],
        stdout: str,
        stderr: str,
        success: bool,
        exit_code: int,
    ):
        """Zapisz wykonaną operację."""
        self.entries.append(
            RollbackEntry(
                timestamp=datetime.now().isoformat(),
                command=command,
                rollback_command=rollback_cmd,
                stdout=stdout[:2000],
                stderr=stderr[:1000],
                success=success,
                exit_code=exit_code,
            )
        )
        self._save()

    def get_rollback_commands(self) -> list[tuple[str, str]]:
        """Zwraca listę (komenda, rollback) w odwróconej kolejności."""
        return [
            (e.command, e.rollback_command)
            for e in reversed(self.entries)
            if e.success and e.rollback_command
        ]

    @staticmethod
    def _run_rollback_cmd(rollback_cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            rollback_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def rollback_last(self, n: int = 1, dry_run: bool = False) -> list[dict]:
        """Cofnij ostatnich n operacji.

        Returns:
            Lista wyników rollbacku [{command, rollback_command, success, output}]
        """
        commands = self.get_rollback_commands()[:n]
        results = []

        for orig_cmd, rollback_cmd in commands:
            if dry_run:
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": None,
                        "output": "[DRY-RUN]",
                    }
                )
                continue

            try:
                proc = self._run_rollback_cmd(rollback_cmd)
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": proc.returncode == 0,
                        "output": proc.stdout.strip() or proc.stderr.strip(),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "command": orig_cmd,
                        "rollback_command": rollback_cmd,
                        "success": False,
                        "output": str(e),
                    }
                )

        return results

    def _save(self):
        """Zapisz sesję do pliku JSON."""
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = self.LOG_DIR / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, session_id: str) -> RollbackSession:
        """Załaduj sesję z pliku."""
        path = cls.LOG_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Rollback session '{session_id}' not found")
        data = json.loads(path.read_text())
        session = cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
        )
        session.entries = [RollbackEntry(**e) for e in data["entries"]]
        return session

    @classmethod
    def list_sessions(cls, limit: int = 20) -> list[dict]:
        """Lista ostatnich sesji rollback."""
        if not cls.LOG_DIR.exists():
            return []
        files = sorted(
            cls.LOG_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        sessions = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text())
                sessions.append(
                    {
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "operations": len(data["entries"]),
                        "rollbackable": sum(
                            1
                            for e in data["entries"]
                            if e.get("rollback_command") and e.get("success")
                        ),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions
