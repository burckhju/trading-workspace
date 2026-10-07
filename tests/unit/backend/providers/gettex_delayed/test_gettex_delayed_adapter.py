import gzip
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.core.config.gettex import GettexDelayedSettings
from app.features.market_data.domain.enums import CacheStatus
from app.features.market_data.persistence.quote_identity import QuoteIdentity
from app.features.market_data.service.errors import (
    MarketDataAuthorizationError,
    MarketDataInvalidResponseError,
)
from app.features.market_data.service.types import WarrantQuoteRequest
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
    batch, retrieved_at = loaded
    quotes = batch.quotes
    assert not batch.errors
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


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_first", [False, True])
async def test_invalid_other_product_does_not_poison_shared_file_cache(
    monkeypatch: pytest.MonkeyPatch, bad_first: bool
) -> None:
    content = (
        b"DE000UN37224,20:55:00.000001,EUR,1.23,100,1.24,100\n"
        b"IE000HFBJ0U0,20:56:00.000001,EUR,19.128,600,0,600\n"
    )
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        payload = (
            b"IE000HFBJ0U0,21:05:00.000001,EUR,19.128,600,19.682,600\n"
            if str(request.url).endswith("pretrade.20260916.21.15.mund.csv.gz")
            else content
        )
        return httpx.Response(200, content=gzip.compress(payload))

    good = WarrantQuoteRequest(uuid4(), uuid4(), uuid4(), datetime(2026, 9, 16, 21, tzinfo=UTC))
    bad = replace(good, warrant_listing_id=uuid4())
    identities = {
        good.warrant_listing_id: QuoteIdentity("good", "DE000UN37224", None, "EUR", "MUND", "MUND"),
        bad.warrant_listing_id: QuoteIdentity("bad", "IE000HFBJ0U0", None, "EUR", "MUND", "MUND"),
    }

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        monkeypatch.setattr(
            adapter,
            "_resolve_identity",
            AsyncMock(side_effect=lambda req: identities[req.warrant_listing_id]),
        )
        monkeypatch.setattr(
            adapter, "_tracked_isins", AsyncMock(return_value={"DE000UN37224", "IE000HFBJ0U0"})
        )
        for request in ([bad, good, bad] if bad_first else [good, bad, good]):
            if request is bad:
                with pytest.raises(
                    MarketDataInvalidResponseError, match="GETTEX_ROW_ASK_NOT_POSITIVE"
                ):
                    await adapter.get_warrant_listing_quote(request)
            else:
                quote = await adapter.get_warrant_listing_quote(request)
                assert quote.data is not None
                assert quote.data.bid == Decimal("1.23")
                assert quote.data.ask == Decimal("1.24")
                assert quote.data.observed_at == datetime(2026, 9, 16, 20, 55, 0, 1, tzinfo=UTC)
        cached = await adapter.get_warrant_listing_quote(good)
        assert cached.cache_status is CacheStatus.HIT
        assert cached.retrieved_at == quote.retrieved_at
        assert len(calls) == 1
        recovered = await adapter.get_warrant_listing_quote(
            replace(bad, as_of=datetime(2026, 9, 16, 21, 15, tzinfo=UTC))
        )
        assert recovered.data is not None
        assert recovered.data.bid == Decimal("19.128")
        assert recovered.data.ask == Decimal("19.682")
        assert recovered.data.observed_at == datetime(2026, 9, 16, 21, 5, 0, 1, tzinfo=UTC)
        assert recovered.data.refresh_error is None
        assert recovered.data.retained is False
    assert len(calls) == 2
