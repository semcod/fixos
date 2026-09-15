"""Safe, DNS-backed observation of configured service endpoints.

The configured hostname is deliberately never replaced with a resolved IP.
That preserves TLS/SNI and lets the normal networking stack follow DNS changes.
The process-local cache contains only operational metadata (host, port,
addresses and timestamps), never credentials, URL paths or query strings.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable, MutableMapping
from urllib.parse import urlsplit

DEFAULT_REFRESH_INTERVAL = 300
DEFAULT_STALE_WINDOW = 86400
_OBSERVATIONS: dict[str, dict[str, Any]] = {}

Resolver = Callable[..., list[tuple[Any, ...]]]


@dataclass(frozen=True)
class EndpointStatus:
    """Permission-safe result of one endpoint observation."""

    name: str
    hostname: str
    port: int | None
    addresses: tuple[str, ...]
    source: str
    observed_at: float | None = None
    changed: bool = False
    stale: bool = False
    error: str | None = None

    @property
    def address_text(self) -> str:
        """Return a compact display value without exposing URL credentials."""
        return ", ".join(self.addresses) or "brak"


def _valid_observation(value: Any) -> bool:
    addresses = value.get("addresses") if isinstance(value, dict) else None
    valid_addresses = isinstance(addresses, list) and all(
        isinstance(item, str) and _is_ip_address(item) for item in addresses
    )
    return (
        isinstance(value, dict)
        and isinstance(value.get("hostname"), str)
        and valid_addresses
        and isinstance(value.get("observed_at"), (int, float))
    )


def _is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _endpoint_parts(url: str) -> tuple[str, int | None]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("endpoint URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("endpoint URL must not contain credentials")
    if not parsed.hostname:
        raise ValueError("endpoint URL must contain a hostname")
    return parsed.hostname, parsed.port


def _resolve_addresses(
    hostname: str, port: int | None, resolver: Resolver
) -> tuple[str, ...]:
    results = resolver(hostname, port, type=socket.SOCK_STREAM)
    addresses: list[str] = []
    for result in results:
        if len(result) < 5:
            continue
        sockaddr = result[4]
        if not isinstance(sockaddr, tuple) or not sockaddr:
            continue
        address = sockaddr[0]
        try:
            normalized = str(ipaddress.ip_address(address))
        except ValueError:
            continue
        if normalized not in addresses:
            addresses.append(normalized)
    if not addresses:
        raise OSError(f"DNS returned no usable addresses for {hostname}")
    return tuple(addresses)


def refresh_endpoint(
    name: str,
    url: str,
    *,
    observations: MutableMapping[str, dict[str, Any]] | None = None,
    interval: int = DEFAULT_REFRESH_INTERVAL,
    now: float | None = None,
    force: bool = False,
    resolver: Resolver = socket.getaddrinfo,
) -> EndpointStatus:
    """Observe one endpoint and retain the last good result on DNS failure.

    This function never changes ``url`` and never makes a service request. A
    stale result is explicitly marked so callers cannot mistake it for a
    current health assertion.
    """
    if not name or not isinstance(name, str):
        raise ValueError("endpoint name must be a non-empty string")
    hostname, port = _endpoint_parts(url)
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        return EndpointStatus(
            name=name,
            hostname=hostname,
            port=port,
            addresses=(str(literal),),
            source="ip-literal",
            error="configure a stable DNS hostname to follow future IP changes",
        )

    observation_store = observations if observations is not None else _OBSERVATIONS
    current_time = time.time() if now is None else now
    previous = observation_store.get(name)
    if previous is not None and not _valid_observation(previous):
        previous = None
    same_target = bool(
        previous
        and previous.get("hostname") == hostname
        and previous.get("port") == port
    )
    age = current_time - float(previous["observed_at"]) if same_target else None
    if (
        not force
        and same_target
        and age is not None
        and age >= 0
        and age < max(0, interval)
    ):
        return EndpointStatus(
            name=name,
            hostname=hostname,
            port=port,
            addresses=tuple(previous["addresses"]),
            source="cache",
            observed_at=float(previous["observed_at"]),
        )

    try:
        addresses = _resolve_addresses(hostname, port, resolver)
    except (OSError, socket.gaierror, ValueError) as exc:
        can_use_stale = (
            same_target
            and age is not None
            and age >= 0
            and age <= max(DEFAULT_STALE_WINDOW, max(0, interval) * 12)
        )
        return EndpointStatus(
            name=name,
            hostname=hostname,
            port=port,
            addresses=tuple(previous["addresses"]) if can_use_stale else (),
            source="stale-cache" if can_use_stale else "error",
            observed_at=float(previous["observed_at"]) if can_use_stale else None,
            stale=can_use_stale,
            error=f"{type(exc).__name__}: {exc}",
        )

    changed = bool(
        previous and same_target and tuple(previous["addresses"]) != addresses
    )
    observation_store[name] = {
        "hostname": hostname,
        "port": port,
        "addresses": list(addresses),
        "observed_at": current_time,
    }
    return EndpointStatus(
        name=name,
        hostname=hostname,
        port=port,
        addresses=addresses,
        source="dns",
        observed_at=current_time,
        changed=changed,
    )


__all__ = ["EndpointStatus", "refresh_endpoint"]
