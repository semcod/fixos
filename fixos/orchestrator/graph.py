"""
Problem Graph – model danych dla kaskadowych problemów systemowych.
Każdy problem może mieć przyczyny (caused_by) i skutki (may_cause),
tworząc DAG (directed acyclic graph) zależności.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

ProblemStatus = Literal["pending", "in_progress", "resolved", "failed", "blocked"]
ProblemSeverity = Literal["critical", "warning", "info"]


@dataclass
class Problem:
    id: str
    description: str
    severity: ProblemSeverity
    fix_commands: list[str]
    status: ProblemStatus = "pending"
    caused_by: list[str] = field(default_factory=list)
    may_cause: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 3

    @property
    def name(self) -> str:
        return self.description

    def is_actionable(self) -> bool:
        return self.status == "pending" and self.attempts < self.max_attempts

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "attempts": self.attempts,
            "caused_by": self.caused_by,
            "fix_commands": self.fix_commands,
        }


class ProblemGraph:
    """
    DAG problemów systemowych z topological sort do wyznaczania kolejności napraw.
    Problemy bez nierozwiązanych zależności są actionable.
    """

    def __init__(self):
        self.nodes: dict[str, Problem] = {}
        self.execution_order: list[str] = []

    @property
    def edges(self) -> list[tuple[str, str]]:
        return [
            (dep, p.id)
            for p in self.nodes.values()
            for dep in p.caused_by
            if dep in self.nodes
        ]

    def add(self, problem: Problem) -> None:
        self.nodes[problem.id] = problem
        self._recalculate_order()

    def get(self, problem_id: str) -> Problem | None:
        return self.nodes.get(problem_id)

    def next_actionable(self) -> Problem | None:
        """Zwraca pierwszy problem bez nierozwiązanych zależności."""
        for pid in self.execution_order:
            p = self.nodes[pid]
            if not p.is_actionable():
                continue
            deps_resolved = all(
                self.nodes[dep].status == "resolved"
                for dep in p.caused_by
                if dep in self.nodes
            )
            if deps_resolved:
                return p
        return None

    def all_done(self) -> bool:
        return all(
            p.status in ("resolved", "failed", "blocked") for p in self.nodes.values()
        )

    def pending_count(self) -> int:
        return sum(1 for p in self.nodes.values() if p.status == "pending")

    def summary(self) -> dict:
        by_status: dict[str, list[str]] = {}
        for p in self.nodes.values():
            by_status.setdefault(p.status, []).append(p.id)
        return {
            "total": len(self.nodes),
            "by_status": by_status,
            "execution_order": self.execution_order,
        }

    def render_tree(self) -> str:
        """Renderuje drzewo problemów jako tekst."""
        lines = []
        roots = [p for p in self.nodes.values() if not p.caused_by]
        visited: set[str] = set()

        def _render(pid: str, indent: int = 0):
            if pid in visited or pid not in self.nodes:
                return
            visited.add(pid)
            p = self.nodes[pid]
            icon = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(
                p.severity, "⚪"
            )
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "resolved": "✅",
                "failed": "❌",
                "blocked": "🚫",
            }.get(p.status, "?")
            prefix = "  " * indent + ("└─ " if indent > 0 else "")
            lines.append(f"{prefix}{icon} [{p.id}] {p.description} {status_icon}")
            for child_id in p.may_cause:
                _render(child_id, indent + 1)

        for root in roots:
            _render(root.id)

        # Dodaj orphaned (mają caused_by ale rodzic nie istnieje)
        for p in self.nodes.values():
            if p.id not in visited:
                lines.append(f"  ◦ [{p.id}] {p.description} (orphaned)")

        return "\n".join(lines) if lines else "(brak problemów)"

    def _recalculate_order(self) -> None:
        """Topological sort (Kahn's algorithm) – problemy bez zależności pierwsze."""
        in_degree: dict[str, int] = {pid: 0 for pid in self.nodes}

        for p in self.nodes.values():
            for dep in p.caused_by:
                if dep in self.nodes:
                    in_degree[p.id] = in_degree.get(p.id, 0) + 1

        queue = deque(pid for pid, deg in in_degree.items() if deg == 0)
        order = []

        while queue:
            pid = queue.popleft()
            order.append(pid)
            p = self.nodes[pid]
            for child_id in p.may_cause:
                if child_id in in_degree:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)

        # Dołącz ewentualne cykle (nie powinny wystąpić, ale dla bezpieczeństwa)
        remaining = [pid for pid in self.nodes if pid not in order]
        self.execution_order = order + remaining

        # Sortuj po severity w ramach tej samej warstwy
        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        self.execution_order.sort(
            key=lambda pid: (
                self.nodes[pid].caused_by != [],  # root problems first
                severity_rank.get(self.nodes[pid].severity, 3),
            )
        )
