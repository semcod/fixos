"""Compatibility facade for the shared context-preserving anonymizer."""

from .utils.anonymizer import _get_sensitive
from .utils.anonymizer import anonymize as _anonymize

def get_sensitive_values() -> dict:
    """Return legacy key names without maintaining a second privacy policy."""
    sensitive = _get_sensitive()
    return {
        "hostname": sensitive.get("hostname"),
        "username": sensitive.get("username"),
        "home_dir": sensitive.get("home"),
    }


def anonymize(data_str: str) -> str:
    """Keep the original string-only return shape used by ``llm_shell``."""
    return _anonymize(data_str)[0]
