"""fixos – AI-powered Linux/Windows diagnostics and repair."""

from __future__ import annotations

from pathlib import Path

# Single Source of Truth: check VERSION file in repo root first,
# then fall back to installed package metadata.
_version_file = Path(__file__).resolve().parent.parent / "VERSION"
if _version_file.is_file():
    __version__ = _version_file.read_text(encoding="utf-8").strip()
else:
    try:
        from importlib.metadata import version as _get_version

        __version__ = _get_version("fixos")
    except Exception:
        __version__ = "unknown"
