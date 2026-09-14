"""Real SQL/JSON round trips, with independent runtimes sharing one durable database."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

NOW = datetime(2026, 9, 11, 18, tzinfo=UTC)
ISIN = "DE000VH2LU21"


class SqlSession:
    """Adapt sync SQLite calls, leaving production SQL statements unmocked."""

    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def get(self, model, key):
        return self.session.get(model, key)

    def add(self, model):
        self.session.add(model)

    async def commit(self):
        self.session.commit()


class SqlDatabase:
    def __init__(self, url):
        self.engine = create_engine(url)

    @asynccontextmanager
    async def session_context(self):
        with Session(self.engine, expire_on_commit=False) as session:
            yield SqlSession(session)


@pytest.fixture
def context(tmp_path):
    url = f"sqlite:///{tmp_path}/observations.db"
    database = SqlDatabase(url)
    tables = [
        TradingVenueModel,
        WarrantModel,
        WarrantListingModel,
        WarrantProviderMappingModel,
        WarrantQuoteObservationModel,
    ]
    for model in tables:
        model.__table__.create(database.engine)
    workspace, warrant, listing, venue, mapping = [uuid4() for _ in range(5)]
    common = dict(created_at=NOW, updated_at=NOW, version=1)
    with Session(database.engine) as session:
        session.add_all(
            [
                TradingVenueModel(
                    id=venue,
                    mic="XFRA",
                    name="Frankfurt",
                    country_code="DE",
                    timezone="Europe/Berlin",
                    is_active=True,
                    reference_version="test",
                    **common,
                ),
                WarrantModel(
                    id=warrant,
                    workspace_id=workspace,
                    issuer_id=uuid4(),
                    underlying_id=uuid4(),
                    display_name="Call",
                    isin=ISIN,
                    wkn="VH2LU2",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    **common,
                ),
                WarrantListingModel(
                    id=listing,
                    workspace_id=workspace,
                    warrant_id=warrant,
                    trading_venue_id=venue,
                    symbol=None,
                    quotation_currency_code="EUR",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    **common,
                ),
                WarrantProviderMappingModel(
                    id=mapping,
                    workspace_id=workspace,
                    warrant_listing_id=listing,
                    provider=MarketDataProvider.FRANKFURT_QUOTES,
                    provider_symbol=ISIN,
                    provider_exchange_code="XSC",
                    status=MappingStatus.ACTIVE,
                    validated_at=NOW,
                    **common,
                ),
            ]
        )
        session.commit()
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=listing,
        bid=None,
        ask=None,
        currency="EUR",
        provider_symbol=ISIN,
        provider_exchange_code="XSC",
        observed_at=NOW,
        isin=ISIN,
        reference_price=Decimal("0.231"),
        reference_price_type="LAST_TRADE",
        assessed_at=NOW,
        source_mode="OFFICIAL_WEBSITE_LAST_TRADE",
        venue_mic="XFRA",
    )
    result = MarketDataResult(
        data=quote,
        provider=MarketDataProvider.FRANKFURT_QUOTES,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )
    provider = AsyncMock()
    provider.get_warrant_listing_quote.return_value = result
    request = WarrantQuoteRequest(workspace, listing, uuid4(), NOW, expected_currency="EUR")
    return SimpleNamespace(
        database=database,
        url=url,
        provider=provider,
        request=request,
        result=result,
        warrant=warrant,
        mapping=mapping,
        venue=venue,
    )


def runtime(c, database=None):
    return RetainedWarrantQuoteProvider(
        database or c.database, c.provider, MarketDataProvider.FRANKFURT_QUOTES
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["http", "empty", "invalid", "out_of_order"])
async def test_restart_and_failed_refresh_retain_original_quote_until_new_success(context, failure):
    c = context
    assert await runtime(c).get_warrant_listing_quote(c.request) == c.result
    # Destroy/rebuild DB pool and provider wrapper: no process cache exists.
    c.database.engine.dispose()
    restarted = SqlDatabase(c.url)
    if failure == "http":
        c.provider.get_warrant_listing_quote.side_effect = MarketDataInvalidResponseError(
            "FRANKFURT_HTTP_404"
        )
    elif failure == "empty":
        c.provider.get_warrant_listing_quote.return_value = replace(c.result, data=None)
    elif failure == "invalid":
        c.provider.get_warrant_listing_quote.return_value = replace(
            c.result, data=replace(c.result.data, isin="DE000VH4VNA6")
        )
    else:
        c.provider.get_warrant_listing_quote.return_value = replace(
            c.result, data=replace(c.result.data, observed_at=NOW - timedelta(days=1))
        )
    retained = await runtime(c, restarted).get_warrant_listing_quote(c.request)
    assert retained.data.retained and retained.data.refresh_error
    assert retained.retrieved_at == c.result.retrieved_at
    assert retained.data.observed_at == NOW
    assert retained.data.reference_price == Decimal("0.231")
    assert retained.data.assessed_at > NOW + timedelta(days=1)
    with Session(restarted.engine) as session:
        row = session.scalar(select(WarrantQuoteObservationModel))
        assert row.payload["data"]["refresh_error"] is None
        assert row.payload["data"]["retained"] is False
    c.provider.get_warrant_listing_quote.side_effect = None
    new_time = NOW + timedelta(minutes=1)
    new = replace(
        c.result,
        retrieved_at=new_time,
        data=replace(
            c.result.data,
            observed_at=new_time,
            assessed_at=new_time,
            reference_price=Decimal("0.25"),
        ),
    )
    c.provider.get_warrant_listing_quote.return_value = new
    assert await runtime(c, restarted).get_warrant_listing_quote(c.request) == new
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError("secret-token")
    latest = await runtime(c, restarted).get_warrant_listing_quote(c.request)
    assert latest.data.reference_price == Decimal("0.25")
    assert latest.retrieved_at == new_time
    assert latest.data.refresh_error == "TimeoutError"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", ["workspace", "isin", "currency", "mapping", "inactive", "venue"]
)
async def test_stored_quote_never_crosses_changed_identity(context, change):
    c = context
    await runtime(c).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError()
    request = c.request
    with Session(c.database.engine) as session:
        if change == "workspace":
            request = replace(request, workspace_id=uuid4())
        elif change == "isin":
            session.get(WarrantModel, c.warrant).isin = "DE000VH4VNA6"
        elif change == "currency":
            session.get(WarrantListingModel, request.warrant_listing_id).quotation_currency_code = (
                "USD"
            )
        elif change == "mapping":
            session.get(WarrantProviderMappingModel, c.mapping).status = MappingStatus.DISABLED
        elif change == "inactive":
            session.get(WarrantListingModel, request.warrant_listing_id).lifecycle_status = (
                WarrantLifecycle.INACTIVE
            )
        else:
            session.get(TradingVenueModel, c.venue).mic = "XSTU"
        session.commit()
    with pytest.raises((MarketDataNotFoundError, MarketDataInvalidResponseError)):
        await runtime(c).get_warrant_listing_quote(request)
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [MarketDataConfigurationError, MarketDataMappingError, MarketDataNotFoundError]
)
async def test_configuration_and_mapping_errors_do_not_enable_fallback(context, error):
    c = context
    await runtime(c).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.side_effect = error("disabled")
    with pytest.raises(error):
        await runtime(c).get_warrant_listing_quote(c.request)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["isin", "provider", "future", "quality", "currency", "listing"])
async def test_invalid_first_quote_is_never_saved_or_exposed_as_available(context, change):
    c = context
    result = c.result
    if change == "provider":
        result = replace(result, provider=MarketDataProvider.VONTOBEL_MARKETS)
    elif change == "quality":
        result = replace(result, quality_status=QualityStatus.SUSPICIOUS)
    else:
        fields = {
            "isin": {"isin": "DE000VH4VNA6"},
            "future": {"observed_at": NOW + timedelta(hours=1)},
            "currency": {"currency": "USD"},
            "listing": {"warrant_listing_id": uuid4()},
        }
        result = replace(result, data=replace(result.data, **fields[change]))
    c.provider.get_warrant_listing_quote.return_value = result
    with pytest.raises(MarketDataInvalidResponseError):
        await runtime(c).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)) is None


@pytest.mark.asyncio
async def test_unknown_close_timestamp_is_not_fabricated(context):
    c = context
    c.provider.get_warrant_listing_quote.return_value = replace(
        c.result,
        data=replace(c.result.data, observed_at=None, reference_price_type="PREVIOUS_CLOSE"),
    )
    await runtime(c).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError()
    result = await runtime(c).get_warrant_listing_quote(c.request)
    assert result.data.observed_at is None
    assert result.data.reference_price_type == "PREVIOUS_CLOSE"
    assert result.retrieved_at == NOW
