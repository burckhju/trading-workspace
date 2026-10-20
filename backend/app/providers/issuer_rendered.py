"""Private renderer transport. Product identity is always validated again in the backend."""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from app.features.market_data.domain.issuer_route_evidence import allowed_product_url, product_url

RENDERER_URL = "http://issuer-renderer:8091"
RENDER_SCHEMA = "ISSUER_RENDERED_DOM_V1"
MAX_RENDER_RESPONSE = 12_100_000  # JSON escaping may multiply the 2 MB DOM limit by six.
RENDER_ERRORS = frozenset(
    {
        "ISSUER_RENDERER_BUSY",
        "ISSUER_RENDERER_THROTTLED",
        "ISSUER_RENDERER_UNAVAILABLE",
        "ISSUER_RENDER_TIMEOUT",
        "ISSUER_RENDER_PAGE_TOO_LARGE",
        "ISSUER_RENDER_PRODUCT_INCOMPLETE",
        "ISSUER_RENDER_NAVIGATION_BLOCKED",
        "ISSUER_RENDER_ACCESS_BLOCKED",
        "ISSUER_RENDER_TERMS_REQUIRED",
        "ISSUER_RENDER_REQUEST_LIMIT",
        "ISSUER_RENDER_TRANSPORT_ERROR",
        "ISSUER_RENDER_HTTP_ERROR",
        "ISSUER_RENDER_CONTENT_TYPE_INVALID",
        "ISSUER_RENDER_BROWSER_ERROR",
        "ISSUER_CONSENT_STATE_INVALID",
    }
)


async def fetch_rendered_page(
    provider: str,
    isin: str,
    *,
    client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
) -> tuple[bytes, str, datetime]:
    product_url(provider, isin)  # Validate before making any request.
    try:
        async with (
            client_factory(timeout=40, follow_redirects=False, trust_env=False) as client,
            client.stream(
                "POST", RENDERER_URL + "/render", json={"provider": provider, "isin": isin}
            ) as response,
        ):
            parts, size = [], 0
            async for part in response.aiter_bytes():
                size += len(part)
                if size > MAX_RENDER_RESPONSE:
                    raise ValueError("ISSUER_RENDER_RESPONSE_INVALID")
                parts.append(part)
            payload = json.loads(b"".join(parts))
            if not isinstance(payload, dict):
                raise ValueError("ISSUER_RENDER_RESPONSE_INVALID")
            if response.status_code != 200:
                reason = payload.get("reason")
                if not isinstance(reason, str) or reason not in RENDER_ERRORS:
                    raise ValueError("ISSUER_RENDERER_UNAVAILABLE")
                raise ValueError(reason)
    except (httpx.HTTPError, TimeoutError):
        raise ValueError("ISSUER_RENDERER_UNAVAILABLE") from None
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError("ISSUER_RENDER_RESPONSE_INVALID") from None
    try:
        if (
            payload.get("schema_version") != RENDER_SCHEMA
            or payload.get("provider") != provider
            or payload.get("isin") != isin
            or not isinstance(payload.get("html"), str)
            or not allowed_product_url(payload["source_url"], provider, isin)
        ):
            raise ValueError
        raw = payload["html"].encode("utf-8")
        captured = datetime.fromisoformat(payload["captured_at"])
        if len(raw) > 2_000_000 or captured.utcoffset() is None:
            raise ValueError
        if not 0 <= (datetime.now(UTC) - captured).total_seconds() <= 120:
            raise ValueError
        return raw, payload["source_url"], captured
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("ISSUER_RENDER_RESPONSE_INVALID") from None
