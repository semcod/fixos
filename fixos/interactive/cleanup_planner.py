"""
Interactive Cleanup Planner for fixOS
Groups cleanup actions and provides interactive selection
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CleanupType(Enum):
    CACHE = "cache_cleanup"
    LOG = "log_cleanup"
    TEMP = "temp_cleanup"
    LARGE_FILE = "large_file"
    SYSTEM = "system_cleanup"
    USER = "user_cleanup"
    DOCKER = "docker_cleanup"
    PACKAGE_MGR = "package_cleanup"


@dataclass
class CleanupAction:
    """Represents a cleanup action"""

    type: CleanupType
    priority: Priority
    path: str
    size_gb: float
    description: str
    command: str
    safe: bool
    impact: str
    category: str = ""
    estimated_time: str = ""
    dependencies: list[str] = None
    preview_command: str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class CleanupPlanner:
    """Interactive cleanup planning and grouping system"""

    def __init__(self):
        self.categories = {
            "cache": {
                "name": "Cache Files",
                "description": "Application cache that can be safely cleared",
                "color": "blue",
                "icon": "",
            },
            "logs": {
                "name": "Log Files",
                "description": "Old system and application logs",
                "color": "yellow",
                "icon": "",
            },
            "temp": {
                "name": "Temporary Files",
                "description": "Temporary files and directories",
                "color": "orange",
                "icon": "",
            },
            "large_files": {
                "name": "Large Files",
                "description": "Large individual files requiring review",
                "color": "red",
                "icon": "",
            },
            "system": {
                "name": "System Cleanup",
                "description": "System-level cleanup operations",
                "color": "purple",
                "icon": "",
            },
            "user": {
                "name": "User Data",
                "description": "User-specific cleanup actions",
                "color": "green",
                "icon": "",
            },
            "docker": {
                "name": "Docker & Containers",
                "description": "Unused images, containers, and volumes",
                "color": "cyan",
                "icon": "",
            },
            "package_manager": {
                "name": "Package Cache",
                "description": "Cached system packages (apt/dnf/pacman)",
                "color": "magenta",
                "icon": "",
            },
        }

        self.impact_levels = {
            "high": {"name": "High Impact", "gain_gb": "> 1.0 GB", "color": "green"},
            "medium": {
                "name": "Medium Impact",
                "gain_gb": "0.1-1.0 GB",
                "color": "yellow",
            },
            "low": {"name": "Low Impact", "gain_gb": "< 0.1 GB", "color": "red"},
        }

    def group_by_category(
        self, suggestions: list[dict]
    ) -> dict[str, list[CleanupAction]]:
        """Group cleanup suggestions by category"""
        grouped = {}

        for suggestion in suggestions:
            try:
                # Convert dict to CleanupAction
                action = self._dict_to_action(suggestion)

                # Determine category
                category = self._get_category_for_action(action)

                if category not in grouped:
                    grouped[category] = []
                grouped[category].append(action)

            except Exception:  # noqa: BLE001, S112 - one malformed suggestion must not drop the whole plan
                continue

        # Sort actions within each category by priority and size
        for actions in grouped.values():
            actions.sort(
                key=lambda x: (self._priority_score(x.priority), x.size_gb),
                reverse=True,
            )

        return grouped

    def prioritize_actions(
        self, grouped_actions: dict[str, list[CleanupAction]]
    ) -> list[CleanupAction]:
        """Create prioritized list of all actions"""
        all_actions = []

        # Add high priority actions first
        for actions in grouped_actions.values():
            high_priority = [
                a for a in actions if a.priority in [Priority.CRITICAL, Priority.HIGH]
            ]
            all_actions.extend(high_priority)

        # Add medium priority actions
        for actions in grouped_actions.values():
            medium_priority = [a for a in actions if a.priority == Priority.MEDIUM]
            all_actions.extend(medium_priority)

        # Add low priority actions
        for actions in grouped_actions.values():
            low_priority = [a for a in actions if a.priority == Priority.LOW]
            all_actions.extend(low_priority)

        # Sort by impact and safety
        all_actions.sort(
            key=lambda x: (
                self._priority_score(x.priority),
                x.size_gb if x.safe else 0,
                x.safe,
            ),
            reverse=True,
        )

        return all_actions

    def create_cleanup_plan(self, suggestions: list[dict]) -> dict[str, Any]:
        """Create comprehensive cleanup plan"""
        grouped = self.group_by_category(suggestions)
        prioritized = self.prioritize_actions(grouped)

        # Calculate statistics
        total_size_gb = sum(action.size_gb for action in prioritized)
        safe_size_gb = sum(action.size_gb for action in prioritized if action.safe)
        high_priority_size = sum(
            action.size_gb
            for action in prioritized
            if action.priority in [Priority.CRITICAL, Priority.HIGH]
        )

        plan = {
            "summary": {
                "total_actions": len(prioritized),
                "total_size_gb": round(total_size_gb, 2),
                "safe_size_gb": round(safe_size_gb, 2),
                "high_priority_size_gb": round(high_priority_size, 2),
                "categories_count": len(grouped),
            },
            "categories": {},
            "prioritized_actions": [],
            "recommendations": self._generate_recommendations(grouped, prioritized),
        }

        # Add category details
        for category, actions in grouped.items():
            category_info = self.categories.get(
                category,
                {
                    "name": category.title(),
                    "description": "Cleanup actions",
                    "color": "gray",
                    "icon": "📁",
                },
            )

            plan["categories"][category] = {
                "info": category_info,
                "actions_count": len(actions),
                "total_size_gb": round(sum(a.size_gb for a in actions), 2),
                "safe_size_gb": round(sum(a.size_gb for a in actions if a.safe), 2),
                "actions": [
                    self._action_to_dict(a) for a in actions[:5]
                ],  # Top 5 per category
            }

        # Add prioritized actions (top 15)
        plan["prioritized_actions"] = [
            self._action_to_dict(a) for a in prioritized[:15]
        ]

        return plan

    def interactive_selection(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Interactive selection process (simulated for now)"""
        selected_actions = []

        # Auto-select safe, high-impact actions
        for action_dict in plan["prioritized_actions"]:
            if action_dict.get("safe", False) and action_dict.get("size_gb", 0) > 0.1:
                selected_actions.append(action_dict)

        return {
            "selected_actions": selected_actions,
            "total_selected": len(selected_actions),
            "estimated_space_gb": round(
                sum(a.get("size_gb", 0) for a in selected_actions), 2
            ),
            "selection_method": "auto_safe_high_impact",
        }

    def _dict_to_action(self, suggestion: dict) -> CleanupAction:
        """Convert dictionary suggestion to CleanupAction"""
        try:
            # Need to handle strings if suggestion payload comes in as string not Enum
            ctype_val = suggestion.get("type", "large_file")
            try:
                ctype = CleanupType(ctype_val)
            except ValueError:
                ctype = CleanupType.LARGE_FILE

            prio_val = suggestion.get("priority", "low")
            try:
                prio = Priority(prio_val)
            except ValueError:
                prio = Priority.LOW

            return CleanupAction(
                type=ctype,
                priority=prio,
                path=suggestion.get("path", ""),
                size_gb=float(suggestion.get("size_gb", 0)),
                description=suggestion.get("description", ""),
                command=suggestion.get("command", ""),
                safe=bool(suggestion.get("safe", False)),
                impact=suggestion.get("impact", "low"),
                category=suggestion.get("category", ""),
                estimated_time=suggestion.get("estimated_time", ""),
                dependencies=suggestion.get("dependencies", []),
                preview_command=suggestion.get("preview_command", ""),
            )
        except Exception:  # noqa: BLE001 - invalid suggestions become a low-priority default action
            return CleanupAction(
                type=CleanupType.LARGE_FILE,
                priority=Priority.LOW,
                path="",
                size_gb=0,
                description="Invalid action",
                command="",
                safe=False,
                impact="none",
            )

    def _action_to_dict(self, action: CleanupAction) -> dict[str, Any]:
        """Convert CleanupAction to dictionary"""
        return {
            "type": action.type.value,
            "priority": action.priority.value,
            "path": action.path,
            "size_gb": action.size_gb,
            "description": action.description,
            "command": action.command,
            "safe": action.safe,
            "impact": action.impact,
            "category": action.category,
            "estimated_time": action.estimated_time,
            "dependencies": action.dependencies,
            "preview_command": action.preview_command,
        }

    def _get_category_for_action(self, action: CleanupAction) -> str:
        """Determine category for action based on type and path"""
        if action.type == CleanupType.CACHE:
            return "cache"
        elif action.type == CleanupType.LOG:
            return "logs"
        elif action.type == CleanupType.TEMP:
            return "temp"
        elif action.type == CleanupType.LARGE_FILE:
            return "large_files"
        elif action.type.value == "docker_cleanup" or "docker" in action.path.lower():
            return "docker"
        elif action.type.value == "package_cleanup" or action.path == "/var/cache":
            return "package_manager"
        elif "system" in action.path.lower() or action.path.startswith("/"):
            return "system"
        else:
            return "user"

    def _priority_score(self, priority: Priority) -> int:
        """Convert priority to numeric score"""
        scores = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1,
        }
        return scores.get(priority, 1)

    @staticmethod
    def _rec_safe_high_impact(prioritized: list[CleanupAction]) -> list[dict]:
        actions = [
            a
            for a in prioritized
            if a.safe
            and a.size_gb > 0.5
            and a.priority in [Priority.HIGH, Priority.CRITICAL]
        ]
        if not actions:
            return []
        total = sum(a.size_gb for a in actions)
        return [
            {
                "type": "safe_cleanup",
                "priority": "high",
                "title": "Safe High-Impact Cleanup Available",
                "description": f"Can safely free {total:.1f} GB with {len(actions)} actions",
                "actions_count": len(actions),
                "space_gb": round(total, 2),
            }
        ]

    @staticmethod
    def _rec_cache(grouped: dict[str, list[CleanupAction]]) -> list[dict]:
        actions = grouped.get("cache", [])
        if not actions:
            return []
        size = sum(a.size_gb for a in actions)
        if size <= 0.5:
            return []
        return [
            {
                "type": "cache_cleanup",
                "priority": "medium",
                "title": "Cache Cleanup Recommended",
                "description": f"Clear application cache to free {size:.1f} GB",
                "actions_count": len(actions),
                "space_gb": round(size, 2),
            }
        ]

    @staticmethod
    def _rec_logs(grouped: dict[str, list[CleanupAction]]) -> list[dict]:
        actions = grouped.get("logs", [])
        if not actions:
            return []
        size = sum(a.size_gb for a in actions)
        if size <= 0.2:
            return []
        return [
            {
                "type": "log_cleanup",
                "priority": "low",
                "title": "Log Files Can Be Cleaned",
                "description": f"Clean old logs to free {size:.1f} GB",
                "actions_count": len(actions),
                "space_gb": round(size, 2),
            }
        ]

    @staticmethod
    def _rec_manual(prioritized: list[CleanupAction]) -> list[dict]:
        actions = [a for a in prioritized if not a.safe and a.size_gb > 1.0]
        if not actions:
            return []
        size = sum(a.size_gb for a in actions)
        return [
            {
                "type": "manual_review",
                "priority": "medium",
                "title": "Manual Review Required",
                "description": f"{len(actions)} large files ({size:.1f} GB) need manual review",
                "actions_count": len(actions),
                "space_gb": round(size, 2),
            }
        ]

    def _generate_recommendations(
        self, grouped: dict[str, list[CleanupAction]], prioritized: list[CleanupAction]
    ) -> list[dict]:
        """Generate cleanup recommendations"""
        recs: list[dict] = []
        recs.extend(self._rec_safe_high_impact(prioritized))
        recs.extend(self._rec_cache(grouped))
        recs.extend(self._rec_logs(grouped))
        recs.extend(self._rec_manual(prioritized))
        return recs


def main():
    """Test the cleanup planner"""
    # Sample data for testing
    sample_suggestions = [
        {
            "type": "cache_cleanup",
            "priority": "high",
            "path": str(Path.home() / ".cache" / "npm"),
            "size_gb": 2.5,
            "description": "Clear npm cache",
            "command": "npm cache clean --force",
            "safe": True,
            "impact": "high",
        },
        {
            "type": "log_cleanup",
            "priority": "medium",
            "path": "/var/log",
            "size_gb": 0.8,
            "description": "Clean old system logs",
            "command": "find /var/log -name '*.log' -mtime +30 -delete",
            "safe": True,
            "impact": "medium",
        },
    ]

    planner = CleanupPlanner()
    plan = planner.create_cleanup_plan(sample_suggestions)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
