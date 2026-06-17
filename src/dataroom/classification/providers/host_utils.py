"""Host helpers for reasoning provider external/local detection."""

from __future__ import annotations

from urllib.parse import urlparse

DEFAULT_TRUSTED_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def endpoint_host(url: str) -> str:
    """Return lowercase hostname from a URL, or empty string if unparseable."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_trusted_local_host(
    url: str,
    trusted_hosts: frozenset[str] | None = None,
) -> bool:
    """True when the URL host is in the trusted local set (default: localhost variants)."""
    trusted = trusted_hosts or DEFAULT_TRUSTED_LOCAL_HOSTS
    host = endpoint_host(url)
    return bool(host) and host in trusted
