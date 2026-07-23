"""
System diagnostics aggregator.
Delegates to specialized check modules.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .checks import (
    diagnose_audio,
    diagnose_thumbnails,
    diagnose_hardware,
    diagnose_system,
    diagnose_security,
    diagnose_resources,
    diagnose_packages,
    diagnose_storage,
    diagnose_files,
)

# Module registry for diagnostic orchestration
DIAGNOSTIC_MODULES = {
    "system": ("🖥️  System (CPU/RAM/dyski/usługi)", diagnose_system),
    "audio": ("🔊 Dźwięk (ALSA/PipeWire/SOF/mikrofon)", diagnose_audio),
    "thumbnails": ("🖼️  Podglądy plików (thumbnails)", diagnose_thumbnails),
    "hardware": ("🔧 Sprzęt (kamera/touchpad/ACPI/DMI)", diagnose_hardware),
    "security": ("🔒 Bezpieczeństwo (firewall/porty/SELinux/SSH)", diagnose_security),
    "resources": ("📊 Zasoby (dysk/pamięć/procesy/autostart)", diagnose_resources),
    "packages": ("📦 Pakiety (nieużywane/osierocone/duplikaty)", diagnose_packages),
    "storage": ("💾 Dyski/partycje (resize/btrfs/optymalizacja)", diagnose_storage),
    "files": ("📂 Pliki (duże/duplikaty/media/archiwizacja)", diagnose_files),
}

# A full recursive file inventory traverses a large home directory many times.
# Keep it available explicitly while making the default LLM diagnosis finish
# promptly on developer workstations with large Docker/model stores.
DEFAULT_DIAGNOSTIC_MODULES = tuple(key for key in DIAGNOSTIC_MODULES if key != "files")


def _run_diagnostic(fn) -> Any:
    try:
        return fn()
    except Exception as exc:
        return {"error": str(exc)}


def get_full_diagnostics(
    modules: list[str] | None = None,
    progress_callback=None,
) -> dict[str, Any]:
    """
    Zbiera diagnostykę z wybranych modułów.

    Args:
        modules: Lista modułów do uruchomienia (None = wszystkie)
        progress_callback: Funkcja (name, description) -> None do aktualizacji UI
    """
    requested = modules or list(DIAGNOSTIC_MODULES)
    if "all" in requested:
        requested = list(DIAGNOSTIC_MODULES)
    selected = list(
        dict.fromkeys(key for key in requested if key in DIAGNOSTIC_MODULES)
    )

    if not selected:
        return {}

    for key in selected:
        desc, fn = DIAGNOSTIC_MODULES[key]
        if progress_callback:
            progress_callback(key, desc)
        else:
            print(f"  → {desc}...", end="\r", flush=True)

    # Modules are independent read-only probes. Running them concurrently
    # changes a many-minute sum of command timeouts into roughly the duration
    # of the slowest module while retaining deterministic result ordering.
    collected: dict[str, Any] = {}
    max_workers = min(4, len(selected))
    with ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="fixos-diagnostics"
    ) as executor:
        future_to_key = {
            executor.submit(_run_diagnostic, DIAGNOSTIC_MODULES[key][1]): key
            for key in selected
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            collected[key] = future.result()

    result = {key: collected[key] for key in selected}

    if not progress_callback:
        print("  → Diagnostyka zakończona.  ")

    return result


# Re-export all diagnostic functions for backward compatibility
__all__ = [
    "get_full_diagnostics",
    "diagnose_audio",
    "diagnose_thumbnails",
    "diagnose_hardware",
    "diagnose_system",
    "diagnose_security",
    "diagnose_resources",
    "diagnose_packages",
    "diagnose_storage",
    "diagnose_files",
    "DIAGNOSTIC_MODULES",
]
