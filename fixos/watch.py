"""
Watch mode daemon for fixOS — periodic diagnostics with desktop notifications.

Usage:
    fixos watch --interval 300 --modules system,security --alert-on critical
"""

from __future__ import annotations

import logging
import platform
import subprocess
import time
from typing import Optional

from fixos.plugins.base import Severity
from fixos.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class WatchDaemon:
    """Daemon wykonujący cykliczną diagnostykę z powiadomieniami."""

    def __init__(
        self,
        interval: int = 300,
        modules: Optional[list[str]] = None,
        alert_on: Severity = Severity.CRITICAL,
        max_iterations: int = 0,
    ):
        self.interval = interval
        self.modules = modules
        self.alert_on = alert_on
        self.max_iterations = max_iterations  # 0 = infinite
        self.registry = PluginRegistry()
        self.registry.discover()
        self._previous_findings: set[str] = set()
        self._previous_resource_alerts: set[str] = set()
        self._iteration = 0
        self._running = True

    def run(self):
        """Główna pętla monitorowania."""
        mods = ", ".join(self.modules) if self.modules else "all"
        print(
            f"fixOS watch: co {self.interval}s, moduły: {mods}, alert: {self.alert_on.value}"
        )
        print("Naciśnij Ctrl+C aby zakończyć.\n")

        try:
            while self._running:
                self._iteration += 1
                if self.max_iterations and self._iteration > self.max_iterations:
                    print("Osiągnięto limit iteracji.")
                    break

                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Iteracja {self._iteration} — diagnostyka...")

                from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

                quick = collect_quick_snapshot(hours=6)
                quick_alerts = self._check_quick_alerts(quick)
                disk = quick["resources"]["disk"]
                memory = quick["resources"]["memory"]
                print(
                    f"  Zasoby: dysk {disk['percent']:.0f}%, "
                    f"RAM {memory['percent']:.0f}%, "
                    f"CPU {quick['resources']['cpu']['percent']:.0f}%"
                )

                results = self.registry.run(modules=self.modules)
                new_alerts = quick_alerts + self._check_for_new_issues(results)

                if new_alerts:
                    for alert in new_alerts:
                        self._notify(alert)
                        print(f"  ALERT: {alert}")
                else:
                    total_findings = sum(len(r.findings) for r in results)
                    print(f"  OK — {total_findings} findings, brak nowych alertów.")

                if self._running and (
                    not self.max_iterations or self._iteration < self.max_iterations
                ):
                    time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\nWatch mode zakończony.")

    def stop(self):
        """Zatrzymaj daemon."""
        self._running = False

    def _check_for_new_issues(self, results) -> list[str]:
        """Wykryj nowe problemy porównując z poprzednią iteracją."""
        severity_order = ["ok", "info", "warning", "critical"]
        alert_level = severity_order.index(self.alert_on.value)

        current = set()
        alerts = []
        for r in results:
            for f in r.findings:
                key = f"{r.plugin_name}:{f.title}"
                current.add(key)
                finding_level = severity_order.index(f.severity.value)
                if key not in self._previous_findings and finding_level >= alert_level:
                    alerts.append(
                        f"[{f.severity.value.upper()}] {r.plugin_name}: "
                        f"{f.title} — {f.description}"
                    )
        self._previous_findings = current
        return alerts

    def _check_quick_alerts(self, snapshot: dict) -> list[str]:
        """Convert resource pressure and growth into de-duplicated watch alerts."""
        severity_order = ["ok", "info", "warning", "critical"]
        alert_level = severity_order.index(self.alert_on.value)
        current: set[str] = set()
        alerts: list[str] = []
        for alert in snapshot.get("alerts", []):
            key = f"{alert['resource']}:{alert['message']}"
            current.add(key)
            severity = alert.get("severity", "warning")
            if (
                key not in self._previous_resource_alerts
                and severity_order.index(severity) >= alert_level
            ):
                alerts.append(f"[{severity.upper()}] zasoby: {alert['message']}")
        self._previous_resource_alerts = current
        return alerts

    @staticmethod
    def _notify(message: str):
        """Desktop notification (Linux: notify-send, macOS: osascript)."""
        system = platform.system()
        try:
            if system == "Linux":
                subprocess.run(
                    ["notify-send", "fixOS Alert", message[:256]],
                    capture_output=True,
                    timeout=5,
                )
            elif system == "Darwin":
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display notification "{message[:256]}" with title "fixOS"',
                    ],
                    capture_output=True,
                    timeout=5,
                )
        except Exception:
            pass  # notifications are best-effort
