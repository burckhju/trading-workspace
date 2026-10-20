"""Missing feed windows must retain verified history and disclose failed refreshes."""

import gzip
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_fixtures
from tests.unit.backend.features.position_monitoring import test_product_valuation as pv_test

from app.core.config.gettex import GettexDelayedSettings
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.service.errors import (
    MarketDataNotFoundError,
    MarketDataUnavailableError,
)
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
    ProductValuationStatus,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
    QuoteSourceAttemptStatus,
)
from app.providers.gettex_delayed.adapter import GettexDelayedWarrantQuoteAdapter

context = retained_fixtures.context

PROVIDER = MarketDataProvider.GETTEX_DELAYED
ERROR = "GETTEX_DELAYED_RECENT_FILE_NOT_AVAILABLE"
FRIDAY = datetime(2026, 9, 25, 19, 14, tzinfo=UTC)
SUNDAY = datetime(2026, 9, 27, 19, 15, tzinfo=UTC)


@pytest.fixture
def gettex_context(context):
    c = context
    with Session(c.database.engine) as session:
        mapping = session.get(WarrantProviderMappingModel, c.mapping)
        mapping.provider = PROVIDER
        mapping.provider_exchange_code = "MUND"
        session.get(TradingVenueModel, c.venue).mic = "MUND"
        session.commit()
    c.result = replace(
        c.result,
        provider=PROVIDER,
        retrieved_at=FRIDAY + timedelta(minutes=4),
        data=replace(
            c.result.data,
            bid=Decimal("0.030"),
            ask=Decimal("0.140"),
            reference_price=None,
            reference_price_type=None,
            observed_at=FRIDAY,
            assessed_at=FRIDAY + timedelta(minutes=4),
            provider_exchange_code="MUND",
            venue_mic="MUND",
            source_mode="OFFICIAL_DELAYED_PRETRADE",
            trading_status="UNKNOWN",
            max_quote_age_seconds=3600,
            feed_delay_seconds=900,
        ),
    )
    c.provider.get_warrant_listing_quote.return_value = c.result
    c.request = replace(c.request, as_of=SUNDAY)
    return c


def missing_files_adapter(c, client, monkeypatch):
    adapter = GettexDelayedWarrantQuoteAdapter(
        database=c.database,
        settings=GettexDelayedSettings(
            enabled=True, private_use_confirmed=True, fallback_windows=3
        ),
        client=client,
    )
    monkeypatch.setattr(adapter, "_tracked_isins", AsyncMock(return_value={c.result.data.isin}))
    return adapter


@pytest.mark.asyncio
async def test_missing_files_are_unavailable_not_a_missing_mapping(gettex_context, monkeypatch):
    c = gettex_context
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = missing_files_adapter(c, client, monkeypatch)
        for _ in range(2):
            with pytest.raises(MarketDataUnavailableError, match=ERROR) as caught:
                await adapter.get_warrant_listing_quote(c.request)
            assert caught.value.retryable is True
            assert caught.value.provider is PROVIDER
    assert len(requests) == 3  # Failed windows keep their existing retry budget.


@pytest.mark.asyncio
async def test_selected_gettex_retains_history_across_restart_and_reports_error(
    gettex_context, monkeypatch
):
    c = gettex_context
    await RetainedWarrantQuoteProvider(c.database, c.provider, PROVIDER).get_warrant_listing_quote(
        c.request
    )
    c.database.engine.dispose()
    fallback = AsyncMock()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(404))
    ) as client:
        adapter = missing_files_adapter(c, client, monkeypatch)
        retained = RetainedWarrantQuoteProvider(c.database, adapter, PROVIDER)
        resolver = MultiSourceWarrantQuoteResolver(
            (
                NamedWarrantQuoteSource(PROVIDER.value, retained, delayed=True),
                NamedWarrantQuoteSource("FRANKFURT_QUOTES", fallback),
            )
        )
        resolved = await resolver.resolve_selected(PROVIDER.value, c.request)
        trade, position, _, listing = pv_test._context(external=True)
        trade.workspace_id = c.request.workspace_id
        listing.id = c.request.warrant_listing_id
        selection = SimpleNamespace(
            selection_status="SELECTED",
            selection_reason="UNIQUE_VERIFIED_ROUTE",
            policy_version="POSITION_QUOTE_SOURCE_POLICY_V1",
            warrant_listing_id=listing.id,
            warrant_provider_mapping_id=c.mapping,
            provider=PROVIDER.value,
            identity_key="verified-gettex",
            mapping_version=1,
        )
        monkeypatch.setattr(
            pv_test.valuation_module,
            "read_quote_identity",
            AsyncMock(return_value=SimpleNamespace(key="verified-gettex")),
        )
        value = await ProductPositionValuationService(
            database=pv_test._Database(
                pv_test._Session(
                    trade=trade,
                    position=position,
                    scalars=[selection, listing, SimpleNamespace(id=c.mapping)],
                )
            ),
            quote_resolver=resolver,
        ).for_trade(trade.id)
        assert value.source_selection_status == "SELECTED"
        assert value.selected_source == PROVIDER.value
        assert value.status is ProductValuationStatus.INDICATIVE
        assert value.reason == "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED"
        assert value.bid == Decimal("0.030")
        assert value.quote_retained is True and value.quote_refresh_error == ERROR
        assert value.quote_observed_at == FRIDAY
        assert value.quote_retrieved_at == c.result.retrieved_at
        assert value.quote_age_limit_exceeded is True
        assert value.market_value is None and value.valuation_usable is False
        assert value.execution_usable is False
        assert value.analysis_market_value == Decimal("0.030") * position.open_quantity
    assert resolved.result is not None
    assert resolved.selected_source == PROVIDER.value
    quote = resolved.result.data
    assert quote.bid == Decimal("0.030") and quote.ask == Decimal("0.140")
    assert quote.observed_at == FRIDAY
    assert resolved.result.retrieved_at == c.result.retrieved_at
    assert quote.retained is True and quote.refresh_error == ERROR
    assert (quote.assessed_at - quote.observed_at).total_seconds() > 3600
    assert quote.trading_status == "UNKNOWN"
    assert len(resolved.attempts) == 1
    assert resolved.attempts[0].reason == "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED"
    assert resolved.attempts[0].refresh_error == ERROR
    fallback.get_warrant_listing_quote.assert_not_awaited()
    with Session(c.database.engine) as session:
        payload = session.scalar(select(WarrantQuoteObservationModel)).payload
        assert payload["data"]["refresh_error"] is None
        assert payload["data"]["retained"] is False
    # A subsequent successful refresh replaces the old observation normally.
    c.provider.get_warrant_listing_quote.return_value = replace(
        c.result,
        retrieved_at=FRIDAY + timedelta(minutes=5),
        data=replace(c.result.data, bid=Decimal("0.040")),
    )
    # Keep source assessment and retrieval times internally consistent.
    new = c.provider.get_warrant_listing_quote.return_value
    c.provider.get_warrant_listing_quote.return_value = replace(
        new, data=replace(new.data, assessed_at=new.retrieved_at)
    )
    latest = await RetainedWarrantQuoteProvider(
        c.database, c.provider, PROVIDER
    ).get_warrant_listing_quote(c.request)
    assert latest.data.bid == Decimal("0.040")
    assert latest.data.refresh_error is None and latest.data.retained is False


@pytest.mark.asyncio
async def test_missing_files_without_history_remain_visible(gettex_context, monkeypatch):
    c = gettex_context
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(404))
    ) as client:
        adapter = missing_files_adapter(c, client, monkeypatch)
        resolver = MultiSourceWarrantQuoteResolver(
            (
                NamedWarrantQuoteSource(
                    PROVIDER.value, RetainedWarrantQuoteProvider(c.database, adapter, PROVIDER)
                ),
            )
        )
        result = await resolver.resolve_selected(PROVIDER.value, c.request)
    assert result.result is None
    assert len(result.attempts) == 1
    assert result.attempts[0].reason == ERROR
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)) is None


@pytest.mark.asyncio
async def test_disabled_mapping_never_reuses_gettex_history(gettex_context):
    c = gettex_context
    retained = RetainedWarrantQuoteProvider(c.database, c.provider, PROVIDER)
    await retained.get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.reset_mock()
    with Session(c.database.engine) as session:
        session.get(WarrantProviderMappingModel, c.mapping).status = MappingStatus.DISABLED
        session.commit()
    resolved = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource(PROVIDER.value, retained),)
    ).resolve_selected(PROVIDER.value, c.request)
    assert resolved.result is None
    assert resolved.attempts[0].reason == "WARRANT_ACTIVE_QUOTE_IDENTITY_NOT_FOUND"
    c.provider.get_warrant_listing_quote.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("selected", [False, True])
async def test_not_found_is_disclosed_for_selected_route_only(gettex_context, selected):
    c = gettex_context
    c.provider.get_warrant_listing_quote.side_effect = MarketDataNotFoundError(
        "https://example.invalid/?token=SECRET"
    )
    resolver = MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource(PROVIDER.value, c.provider),)
    )
    resolved = (
        await resolver.resolve_selected(PROVIDER.value, c.request)
        if selected
        else await resolver.resolve(c.request)
    )
    assert resolved.result is None
    if selected:
        assert resolved.attempts[0].reason == "MarketDataNotFoundError"
        assert resolved.attempts[0].status is QuoteSourceAttemptStatus.MISSING
    else:
        assert resolved.attempts == ()


@pytest.mark.asyncio
async def test_invalid_product_keeps_original_history_and_explicit_row_error(
    gettex_context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = gettex_context
    await RetainedWarrantQuoteProvider(c.database, c.provider, PROVIDER).get_warrant_listing_quote(
        c.request
    )
    content = (
        f"{c.result.data.isin},19:10:00.000001,EUR,0.04,100,0,100\n"
        "DE000UN37224,19:10:01.000001,EUR,1.23,100,1.24,100\n"
    ).encode()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=gzip.compress(content))
        )
    ) as client:
        adapter = missing_files_adapter(c, client, monkeypatch)
        monkeypatch.setattr(
            adapter, "_tracked_isins", AsyncMock(return_value={c.result.data.isin, "DE000UN37224"})
        )
        result = await RetainedWarrantQuoteProvider(
            c.database, adapter, PROVIDER
        ).get_warrant_listing_quote(c.request)
    assert result.data is not None
    assert result.data.retained is True
    assert result.data.refresh_error == "GETTEX_ROW_ASK_NOT_POSITIVE"
    assert result.data.bid == Decimal("0.030")
    assert result.data.observed_at == FRIDAY
    assert result.retrieved_at == c.result.retrieved_at
    with Session(c.database.engine) as session:
        payload = session.scalar(select(WarrantQuoteObservationModel)).payload
        assert payload["data"]["refresh_error"] is None
        assert payload["data"]["retained"] is False
        assert payload["retrieved_at"] == c.result.retrieved_at.isoformat().replace("+00:00", "Z")
