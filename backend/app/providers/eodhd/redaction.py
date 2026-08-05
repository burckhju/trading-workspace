"""Redaction helpers for EODHD secrets and request URLs."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = frozenset({"api_token", "api_key", "token"})
REDACTED = "***REDACTED***"


def redact_query_params(params: Mapping[str, object]) -> dict[str, object]:
    """Return a copy with known credential parameters redacted."""
    return {
        key: REDACTED if key.lower() in SENSITIVE_QUERY_KEYS else value
        for key, value in params.items()
    }


def redact_url(url: str) -> str:
    """Redact known credential query parameters without changing the URL shape."""
    parts = urlsplit(url)
    query = urlencode(
        [
            (key, REDACTED if key.lower() in SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
