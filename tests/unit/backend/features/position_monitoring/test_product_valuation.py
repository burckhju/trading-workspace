from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
    ProductValuationStatus,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


class _ExecuteResult:
    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *, trade, position, evaluation=None, listing=None):
        self._trade = trade
        self._position = position
        self._scalars = [evaluation, listing]

    async def execute(self, _statement):
        return _ExecuteResult((self._trade, self._position))

    async def scalar(self, _statement):
        return self._scalars.pop(0)


class _Database:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def session_context(self):
        yield self._session


class _Provider:
    def __init__(self, result):
        self._result = result

    async def get_warrant_listing_quote(self, _request):
        return self._result


def _context(*, external: bool = False):
    trade_id = uuid4()
    position_id = uuid4()
    evaluation_id = None if external else uuid4()
    listing_id = uuid4()
    trade = SimpleNamespace(
        id=trade_id,
        workspace_id=uuid4(),
        product_evaluation_id=evaluation_id,
    )
    position = SimpleNamespace(
        id=position_id,
        open_quantity=10,
        cost_basis=Decimal("20.00"),
    )
    evaluation = (
        None if external else SimpleNamespace(id=evaluation_id, warrant_listing_id=listing_id)
    )
    listing = SimpleNamespace(
        id=listing_id,
        symbol="TEST12.STU",
        quotation_currency_code="EUR",
    )
    return trade, position, evaluation, listing


def _quote_result(
    *,
    listing_id,
    bid=Decimal("2.50"),
    ask=Decimal("2.55"),
    currency="EUR",
):
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=listing_id,
        bid=bid,
        ask=ask,
        currency=currency,
        provider_symbol="TEST12",
        provider_exchange_code="STU",
        observed_at=NOW,
    )
    return MarketDataResult(
        data=quote,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )


@pytest.mark.asyncio
async def test_values_open_long_position_at_exact_listing_bid() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=listing.id))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.AVAILABLE
    assert result.warrant_listing_id == listing.id
    assert result.bid == Decimal("2.50")
    assert result.market_value == Decimal("25.00")
    assert result.unrealized_gross_pnl == Decimal("5.00")


@pytest.mark.asyncio
async def test_external_trade_without_listing_provenance_is_not_guessed() -> None:
    trade, position, _evaluation, _listing = _context(external=True)
    service = ProductPositionValuationService(
        database=_Database(_Session(trade=trade, position=position)),
        quote_provider=None,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.UNAVAILABLE
    assert result.reason == "WARRANT_LISTING_PROVENANCE_UNAVAILABLE"
    assert result.market_value is None


@pytest.mark.asyncio
async def test_missing_bid_does_not_create_indicative_value() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=listing.id, bid=None))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.MISSING
    assert result.reason == "WARRANT_BID_MISSING"
    assert result.market_value is None
    assert result.unrealized_gross_pnl is None


@pytest.mark.asyncio
async def test_wrong_quote_listing_is_rejected() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=uuid4()))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.ERROR
    assert result.reason == "WARRANT_QUOTE_LISTING_MISMATCH"
    assert result.market_value is None
