"""
Plugin registry with autodiscovery for fixOS diagnostic plugins.

Discovers plugins via:
1. Built-in plugins from fixos.plugins.builtin
2. External plugins registered as entry_points (group: fixos.diagnostics)
"""

from __future__ import annotations

import importlib.metadata
import logging
import time
from collections.abc import Callable

from .base import DiagnosticPlugin, DiagnosticResult, Finding, Severity

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for diagnostic plugins with autodiscovery."""

    ENTRY_POINT_GROUP = "fixos.diagnostics"

    def __init__(self):
        self._plugins: dict[str, DiagnosticPlugin] = {}
        self._results: dict[str, DiagnosticResult] = {}

    def discover(self):
        """Odkrywanie pluginów przez builtin + entry_points."""
        self._register_builtins()
        self._register_external()

    def _register_builtins(self):
        """Rejestracja wbudowanych pluginów."""
        from fixos.plugins.builtin import (
            audio,
            disk,
            dns,
            hardware,
            mesh,
            printers,
            resources,
            security,
            thumbnails,
        )

        for module in [
            audio,
            hardware,
            security,
            resources,
            disk,
            thumbnails,
            printers,
            mesh,
            dns,
        ]:
            plugin = module.Plugin()
            self._plugins[plugin.name] = plugin

    def _register_external(self):
        """Rejestracja zewnętrznych pluginów przez entry_points."""
        try:
            eps = importlib.metadata.entry_points(group=self.ENTRY_POINT_GROUP)
        except TypeError:
            # Python < 3.12 compatibility
            eps = importlib.metadata.entry_points().get(self.ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                plugin_cls = ep.load()
                plugin = plugin_cls()
                if plugin.name in self._plugins:
                    logger.warning(
                        f"Plugin {plugin.name} already registered, "
                        f"skipping external {ep.name}"
                    )
                    continue
                self._plugins[plugin.name] = plugin
                logger.info(f"Loaded external plugin: {plugin.name}")
            except Exception as e:  # noqa: BLE001 - a broken third-party plugin must not stop discovery
                logger.error(f"Failed to load plugin {ep.name}: {e}")

    def register(self, plugin: DiagnosticPlugin):
        """Ręczna rejestracja pluginu."""
        self._plugins[plugin.name] = plugin

    def list_plugins(self, runnable_only: bool = True) -> list[dict]:
        """Lista zarejestrowanych pluginów."""
        plugins = list(self._plugins.values())
        if runnable_only:
            plugins = [p for p in plugins if p.can_run()]
        return [p.get_metadata() for p in plugins]

    def get_plugin(self, name: str) -> DiagnosticPlugin | None:
        """Pobierz plugin po nazwie."""
        return self._plugins.get(name)

    def run(
        self,
        modules: list[str] | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> list[DiagnosticResult]:
        """Uruchom diagnostykę dla wybranych (lub wszystkich) modułów."""
        targets = modules or list(self._plugins.keys())
        results = []

        for name in targets:
            if name not in self._plugins:
                logger.warning(f"Unknown plugin: {name}")
                continue

            plugin = self._plugins[name]
            if not plugin.can_run():
                logger.info(f"Skipping {name} — not available on this platform")
                continue

            if progress_callback:
                progress_callback(name, f"Diagnostyka: {plugin.description}")

            start = time.monotonic()
            try:
                result = plugin.diagnose()
                result.duration_ms = (time.monotonic() - start) * 1000
                results.append(result)
                self._results[name] = result
            except Exception as e:  # noqa: BLE001 - one failing plugin must not abort the others
                logger.error(f"Plugin {name} failed: {e}")
                results.append(
                    DiagnosticResult(
                        plugin_name=name,
                        status=Severity.CRITICAL,
                        findings=[
                            Finding(
                                title=f"Plugin {name} crashed",
                                severity=Severity.CRITICAL,
                                description=str(e),
                            )
                        ],
                    )
                )

        return results

    @property
    def last_results(self) -> dict[str, DiagnosticResult]:
        """Ostatnie wyniki diagnostyki."""
        return dict(self._results)
