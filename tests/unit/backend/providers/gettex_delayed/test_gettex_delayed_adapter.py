import gzip
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.core.config.gettex import GettexDelayedSettings
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
)
from app.features.market_data.persistence.quote_identity import QuoteIdentity
from app.features.market_data.service.errors import (
    MarketDataAuthenticationError,
    MarketDataAuthorizationError,
    MarketDataInvalidResponseError,
    MarketDataRateLimitError,
    MarketDataUnavailableError,
)
from app.features.market_data.service.types import WarrantQuoteRequest
from app.providers.gettex_delayed import adapter as gettex_module
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


_ISIN = "DE000UN37224"
_ADDED_ISIN = "DE000AB00001"
_FILE = "pretrade.20260916.21.00.mund.csv.gz"
_AS_OF = datetime(2026, 9, 16, 21, tzinfo=UTC)
# All prices and timestamps in these transport fixtures are synthetic.
_PAYLOAD = gzip.compress(
    b"DE000UN37224,20:55:00.000001,EUR,1.23,100,1.24,100\n"
    b"DE000AB00001,20:56:00.000001,EUR,2.34,100,2.35,100\n"
)


def _requests_and_identities(monkeypatch, adapter):
    first = WarrantQuoteRequest(uuid4(), uuid4(), uuid4(), _AS_OF)
    added = replace(first, warrant_listing_id=uuid4())
    identities = {
        first.warrant_listing_id: QuoteIdentity("first", _ISIN, None, "EUR", "MUND", "MUND"),
        added.warrant_listing_id: QuoteIdentity("added", _ADDED_ISIN, None, "EUR", "MUND", "MUND"),
    }
    monkeypatch.setattr(
        adapter,
        "_resolve_identity",
        AsyncMock(side_effect=lambda request: identities[request.warrant_listing_id]),
    )
    return first, added


@pytest.mark.asyncio
async def test_expanded_tracked_isins_rescan_once_then_reuse_for_unchanged_or_reduced_set(
    monkeypatch,
) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=_PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        first, added = _requests_and_identities(monkeypatch, adapter)
        tracked = {_ISIN}
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value=tracked))
        original = await adapter.get_warrant_listing_quote(first)
        assert original.data is not None and original.data.bid == Decimal("1.23")

        # Mutating the caller's set must not mutate the cached scan evidence.
        tracked.add(_ADDED_ISIN)
        expanded = await adapter.get_warrant_listing_quote(added)
        assert expanded.data is not None
        assert expanded.data.bid == Decimal("2.34")
        assert expanded.data.ask == Decimal("2.35")
        assert expanded.data.isin == _ADDED_ISIN
        assert expanded.cache_status is CacheStatus.BYPASS
        assert len(calls) == 2

        unchanged = await adapter.get_warrant_listing_quote(first)
        tracked.remove(_ISIN)
        reduced = await adapter.get_warrant_listing_quote(added)
        assert unchanged.cache_status is reduced.cache_status is CacheStatus.HIT
        assert unchanged.retrieved_at == reduced.retrieved_at == expanded.retrieved_at
        assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_row", [b"", b"DE000AB00001,20:56:00.000001,EUR,0,100,2.35,100\n"])
async def test_scanned_missing_or_invalid_isin_does_not_trigger_repeat_downloads(
    monkeypatch, extra_row
) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        content = b"DE000UN37224,20:55:00.000001,EUR,1.23,100,1.24,100\n" + extra_row
        return httpx.Response(200, content=gzip.compress(content))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        first, added = _requests_and_identities(monkeypatch, adapter)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN, _ADDED_ISIN}))
        original = await adapter.get_warrant_listing_quote(first)
        for _ in range(2):
            if extra_row:
                with pytest.raises(
                    MarketDataInvalidResponseError, match="GETTEX_ROW_BID_NOT_POSITIVE"
                ):
                    await adapter.get_warrant_listing_quote(added)
            else:
                missing = await adapter.get_warrant_listing_quote(added)
                assert missing.data is None and missing.cache_status is CacheStatus.HIT
                assert missing.retrieved_at == original.retrieved_at
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_failed_expanded_scan_keeps_verified_cache_for_previously_scanned_isins(
    monkeypatch,
) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=_PAYLOAD if len(calls) == 1 else _PAYLOAD[:-8])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        first, added = _requests_and_identities(monkeypatch, adapter)
        tracked = {_ISIN}
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value=tracked))
        original = await adapter.get_warrant_listing_quote(first)
        tracked.add(_ADDED_ISIN)
        with pytest.raises(MarketDataInvalidResponseError, match="GETTEX_GZIP_INVALID"):
            await adapter.get_warrant_listing_quote(added)
        tracked.remove(_ADDED_ISIN)
        retained_cache = await adapter.get_warrant_listing_quote(first)
        assert retained_cache.cache_status is CacheStatus.HIT
        assert retained_cache.retrieved_at == original.retrieved_at
        assert retained_cache.data.observed_at == original.data.observed_at
        assert len(calls) == 2


@pytest.mark.asyncio
async def test_cache_is_isolated_by_workspace_and_mic(monkeypatch) -> None:
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=_PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN}))
        first_workspace, second_workspace = uuid4(), uuid4()
        for workspace, mic in (
            (first_workspace, "MUND"),
            (second_workspace, "MUND"),
            (first_workspace, "MUNC"),
        ):
            _, _, hit = await adapter._quotes_for(workspace, mic, _AS_OF)
            assert hit is False
            _, _, hit = await adapter._quotes_for(workspace, mic, _AS_OF)
            assert hit is True
    assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retry_after", "expected_seconds"),
    [("120", 120), (None, 60), ("invalid", 60), ("-1", 60), ("0", 60), ("9" * 100, 60)],
)
async def test_rate_limit_preserves_existing_error_contract_and_retry_after(
    monkeypatch, retry_after, expected_seconds
) -> None:
    calls = []
    monkeypatch.setattr(gettex_module, "monotonic", lambda: 1000.0)

    def handler(request):
        calls.append(request)
        headers = {} if retry_after is None else {"Retry-After": retry_after}
        return httpx.Response(429, headers=headers)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        for _ in range(2):
            with pytest.raises(
                MarketDataRateLimitError, match="GETTEX_DELAYED_RATE_LIMITED"
            ) as caught:
                await adapter._download(_FILE, {_ISIN})
            error = caught.value
            assert error.provider is MarketDataProvider.GETTEX_DELAYED
            assert error.capability is MarketDataCapability.WARRANT_LISTING_QUOTE
            assert error.retryable is True
            assert error.retry_after == timedelta(seconds=expected_seconds)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retry_after", "expected_seconds"),
    [
        ("Fri, 30 Oct 2026 12:02:00 GMT", 120),
        ("Fri, 30 Oct 2026 11:59:00 GMT", 60),
        ("Fri, 30 Oct 2026 12:02:00", 60),
    ],
)
async def test_rate_limit_http_date_uses_receipt_time(monkeypatch, retry_after, expected_seconds):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 30, 12, tzinfo=UTC)

    monkeypatch.setattr(gettex_module, "datetime", FrozenDatetime)
    monkeypatch.setattr(gettex_module, "monotonic", lambda: 1000.0)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": retry_after})
        )
    ) as client:
        adapter = _adapter(client=client)
        with pytest.raises(MarketDataRateLimitError) as caught:
            await adapter._download(_FILE, {_ISIN})
        assert caught.value.retry_after == timedelta(seconds=expected_seconds)


@pytest.mark.asyncio
async def test_rate_limit_blocks_new_scans_across_workspace_mic_and_recovers_at_deadline(
    monkeypatch,
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(gettex_module, "monotonic", lambda: clock[0])
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 2:
            return httpx.Response(429, headers={"Retry-After": "120"})
        return httpx.Response(200, content=_PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        tracked = {_ISIN}
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value=tracked))
        workspace = uuid4()
        batch, fetched_at, _ = await adapter._quotes_for(workspace, "MUND", _AS_OF)
        tracked.add(_ADDED_ISIN)
        with pytest.raises(MarketDataRateLimitError):
            await adapter._quotes_for(workspace, "MUND", _AS_OF)
        clock[0] += 30
        for different_workspace, mic in ((uuid4(), "MUND"), (workspace, "MUNC")):
            with pytest.raises(MarketDataRateLimitError) as caught:
                await adapter._quotes_for(different_workspace, mic, _AS_OF)
            assert caught.value.retry_after == timedelta(seconds=90)
        assert len(calls) == 2
        assert not adapter._missing_until

        tracked.remove(_ADDED_ISIN)
        cached_batch, cached_time, hit = await adapter._quotes_for(workspace, "MUND", _AS_OF)
        assert hit is True and cached_batch == batch and cached_time == fetched_at
        tracked.add(_ADDED_ISIN)
        clock[0] += 90
        recovered, _, hit = await adapter._quotes_for(workspace, "MUND", _AS_OF)
        assert hit is False and set(recovered.quotes) == {_ISIN, _ADDED_ISIN}
        assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_length",
    ["", "broken", "-1", "+10", "1.5", "10, 10", "9" * 5000],
    ids=["empty", "text", "negative", "signed", "decimal", "duplicate", "overflow"],
)
async def test_invalid_content_length_is_typed_and_non_retryable(content_length) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"Content-Length": content_length}, content=_PAYLOAD
            )
        )
    ) as client:
        adapter = _adapter(client=client)
        with pytest.raises(
            MarketDataInvalidResponseError, match="GETTEX_DELAYED_CONTENT_LENGTH_INVALID"
        ) as caught:
            await adapter._download(_FILE, {_ISIN})
        assert caught.value.retryable is False


@pytest.mark.asyncio
@pytest.mark.parametrize("difference", [-1, 1])
async def test_content_length_mismatch_never_accepts_a_partial_or_changed_file(difference):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Length": str(len(_PAYLOAD) + difference)},
                content=_PAYLOAD,
            )
        )
    ) as client:
        with pytest.raises(
            MarketDataInvalidResponseError, match="GETTEX_DELAYED_CONTENT_LENGTH_MISMATCH"
        ):
            await _adapter(client=client)._download(_FILE, {_ISIN})


@pytest.mark.asyncio
async def test_outer_http_gzip_length_is_not_compared_with_decoded_file_length():
    encoded_payload = gzip.compress(_PAYLOAD)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Length": str(len(encoded_payload)), "Content-Encoding": "gzip"},
                content=encoded_payload,
            )
        )
    ) as client:
        loaded = await _adapter(client=client)._download(_FILE, {_ISIN})
        assert loaded is not None
        assert loaded[0].quotes[_ISIN].bid == Decimal("1.23")


@pytest.mark.asyncio
@pytest.mark.parametrize("too_large", [False, True])
async def test_stream_without_content_length_still_requires_complete_bounded_gzip(too_large):
    class PayloadStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield _PAYLOAD[:10]
            yield _PAYLOAD[10:]

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=PayloadStream()))
    ) as client:
        adapter = _adapter(
            client=client, max_download_bytes=len(_PAYLOAD) - 1 if too_large else len(_PAYLOAD)
        )
        if too_large:
            with pytest.raises(
                MarketDataInvalidResponseError, match="GETTEX_DELAYED_FILE_TOO_LARGE"
            ):
                await adapter._download(_FILE, {_ISIN})
        else:
            loaded = await adapter._download(_FILE, {_ISIN})
            assert loaded is not None and loaded[0].quotes[_ISIN].ask == Decimal("1.24")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type", "code", "retryable"),
    [
        (401, MarketDataAuthenticationError, "GETTEX_DELAYED_AUTHENTICATION_REQUIRED", False),
        (403, MarketDataAuthorizationError, "GETTEX_DELAYED_ACCESS_FORBIDDEN", False),
        (500, MarketDataUnavailableError, "GETTEX_DELAYED_UPSTREAM_UNAVAILABLE", True),
        (503, MarketDataUnavailableError, "GETTEX_DELAYED_UPSTREAM_UNAVAILABLE", True),
        (206, MarketDataInvalidResponseError, "GETTEX_DELAYED_UNEXPECTED_HTTP_206", False),
        (302, MarketDataInvalidResponseError, "GETTEX_DELAYED_UNEXPECTED_HTTP_302", False),
    ],
)
async def test_http_failures_preserve_provider_contract_and_never_try_an_older_window(
    monkeypatch, status, error_type, code, retryable
):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN}))
        with pytest.raises(error_type, match=code) as caught:
            await adapter._quotes_for(uuid4(), "MUND", _AS_OF)
        assert caught.value.retryable is retryable
        assert caught.value.provider is MarketDataProvider.GETTEX_DELAYED
        assert caught.value.capability is MarketDataCapability.WARRANT_LISTING_QUOTE
        assert len(calls) == 1
        assert not adapter._missing_until


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transport_error", "code"),
    [
        (httpx.ReadTimeout, "GETTEX_DELAYED_TIMEOUT"),
        (httpx.ConnectError, "GETTEX_DELAYED_NETWORK_ERROR"),
    ],
)
async def test_transport_errors_are_retryable_and_do_not_fall_back(
    monkeypatch, transport_error, code
):
    calls = []

    def handler(request):
        calls.append(request)
        raise transport_error("synthetic failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN}))
        with pytest.raises(MarketDataUnavailableError, match=code) as caught:
            await adapter._quotes_for(uuid4(), "MUND", _AS_OF)
        assert caught.value.retryable is True
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_only_missing_file_allows_previous_window_with_original_quote_time(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(404)
        return httpx.Response(
            200, content=gzip.compress(b"DE000UN37224,20:40:00.000001,EUR,1.23,100,1.24,100\n")
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = _adapter(client=client)
        first, _ = _requests_and_identities(monkeypatch, adapter)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN}))
        result = await adapter.get_warrant_listing_quote(first)
        cached = await adapter.get_warrant_listing_quote(first)
        assert result.data.observed_at == datetime(2026, 9, 16, 20, 40, 0, 1, tzinfo=UTC)
        assert result.data.source_mode == "OFFICIAL_DELAYED_PRETRADE"
        assert result.data.feed_delay_seconds == 900 and result.data.trading_status == "UNKNOWN"
        assert cached.retrieved_at == result.retrieved_at and cached.cache_status is CacheStatus.HIT
        assert len(calls) == 2
        assert str(calls[1].url).endswith("pretrade.20260916.20.45.mund.csv.gz")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [b"<html>changed provider response</html>", _PAYLOAD[:-8]])
async def test_changed_or_truncated_payload_never_becomes_a_success(payload):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=payload))
    ) as client:
        with pytest.raises(MarketDataInvalidResponseError, match="GETTEX_GZIP_INVALID"):
            await _adapter(client=client)._download(_FILE, {_ISIN})


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["", "USD"])
async def test_missing_or_conflicting_feed_currency_is_not_replaced(monkeypatch, currency):
    payload = gzip.compress(f"{_ISIN},20:55:00.000001,{currency},1.23,100,1.24,100\n".encode())
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=payload))
    ) as client:
        adapter = _adapter(client=client)
        first, _ = _requests_and_identities(monkeypatch, adapter)
        monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={_ISIN}))
        code = "GETTEX_ROW_CURRENCY_INVALID" if not currency else "GETTEX_DELAYED_CURRENCY_MISMATCH"
        with pytest.raises(MarketDataInvalidResponseError, match=code):
            await adapter.get_warrant_listing_quote(first)


@pytest.mark.asyncio
async def test_expected_currency_mismatch_rejects_before_downloading(monkeypatch):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("unexpected HTTP"))
    )
    async with client:
        adapter = _adapter(client=client)
        first, _ = _requests_and_identities(monkeypatch, adapter)
        with pytest.raises(
            MarketDataInvalidResponseError, match="GETTEX_DELAYED_EXPECTED_CURRENCY_MISMATCH"
        ):
            await adapter.get_warrant_listing_quote(replace(first, expected_currency="USD"))
