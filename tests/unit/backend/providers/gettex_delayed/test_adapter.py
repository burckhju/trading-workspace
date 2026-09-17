import gzip
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.core.config.gettex import GettexDelayedSettings
from app.features.market_data.service.errors import (
    MarketDataAuthorizationError,
    MarketDataInvalidResponseError,
)
from app.providers.gettex_delayed.adapter import GettexDelayedWarrantQuoteAdapter


class _Database:
    pass


def _settings(**overrides) -> GettexDelayedSettings:
    values = {
        "enabled": True,
        "private_use_confirmed": True,
        "fallback_windows": 3,
    }
    values.update(overrides)
    return GettexDelayedSettings(**values)


def _adapter(
    *, client: httpx.AsyncClient | None = None, **overrides
) -> GettexDelayedWarrantQuoteAdapter:
    return GettexDelayedWarrantQuoteAdapter(
        database=_Database(),  # type: ignore[arg-type]
        settings=_settings(**overrides),
        client=client,
    )


def test_gettex_is_disabled_by_default() -> None:
    settings = GettexDelayedSettings()

    assert settings.enabled is False
    assert settings.private_use_confirmed is False
    assert settings.base_url == (
        "https://erdk.bayerische-boerse.de:8000/delayed-data/MUNC-MUND/pretrade"
    )


def test_enabling_requires_explicit_private_use_confirmation() -> None:
    with pytest.raises(ValueError, match="eligible private use"):
        GettexDelayedSettings(enabled=True)


def test_base_url_is_restricted_to_verified_official_endpoint() -> None:
    with pytest.raises(ValueError, match="verified official HTTPS endpoint"):
        GettexDelayedSettings(base_url="https://example.com/pretrade")


def test_candidate_files_use_current_and_previous_quarter_hours() -> None:
    adapter = _adapter()

    names = adapter._candidate_file_names(
        datetime(2026, 9, 17, 10, 28, 32, tzinfo=UTC),
        "MUND",
    )

    assert names == (
        "pretrade.20260917.10.15.mund.csv.gz",
        "pretrade.20260917.10.00.mund.csv.gz",
        "pretrade.20260917.09.45.mund.csv.gz",
    )


@pytest.mark.asyncio
async def test_download_streams_and_filters_verified_gzip_rows() -> None:
    content = "\n".join(
        [
            "DE000UN37224,20:45:00.000001,EUR,1.20,100,1.21,100",
            "DE000UN37224,20:59:00.000001,EUR,1.23,120,1.24,110",
            "IE000HFBJ0U0,20:59:00.000001,EUR,19.128,600,19.682,600",
        ]
    ).encode()
    payload = gzip.compress(content)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/pretrade.20260916.21.00.mund.csv.gz")
        return httpx.Response(200, content=payload, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        loaded = await adapter._download(
            "pretrade.20260916.21.00.mund.csv.gz",
            {"DE000UN37224"},
        )

    assert loaded is not None
    quotes, retrieved_at = loaded
    assert retrieved_at.tzinfo is UTC
    assert set(quotes) == {"DE000UN37224"}
    assert quotes["DE000UN37224"].bid == Decimal("1.23")
    assert quotes["DE000UN37224"].ask == Decimal("1.24")


@pytest.mark.asyncio
async def test_download_returns_none_for_missing_window() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        loaded = await adapter._download(
            "pretrade.20260916.21.00.mund.csv.gz",
            {"DE000UN37224"},
        )

    assert loaded is None


@pytest.mark.asyncio
async def test_download_rejects_forbidden_access() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        with pytest.raises(MarketDataAuthorizationError):
            await adapter._download(
                "pretrade.20260916.21.00.mund.csv.gz",
                {"DE000UN37224"},
            )


@pytest.mark.asyncio
async def test_download_rejects_oversized_payload_before_streaming() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": "1000"},
            content=b"x",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client, max_download_bytes=100)
        with pytest.raises(MarketDataInvalidResponseError, match="FILE_TOO_LARGE"):
            await adapter._download(
                "pretrade.20260916.21.00.mund.csv.gz",
                {"DE000UN37224"},
            )
