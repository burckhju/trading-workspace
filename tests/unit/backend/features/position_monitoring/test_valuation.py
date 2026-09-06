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
from app.features.position_monitoring.service.valuation import (
    PositionValuationService,
    PositionValuationStatus,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


class _ExecuteResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _Session:
    def __init__(self, *, position, trade, evaluation=None, listing=None):
        self._position = position
        self._trade = trade
        self._scalars = [evaluation, listing]

    async def execute(self, _statement):
        return _ExecuteResult((self._position, self._trade))

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


def _quote_result(listing_id, *, bid: str | None, ask: str | None):
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=listing_id,
        bid=Decimal(bid) if bid is not None else None,
        ask=Decimal(ask) if ask is not None else None,
        currency="EUR",
        provider_symbol="TEST.WARRANT",
        provider_exchange_code="XETRA",
        observed_at=NOW,
    )
    return MarketDataResult(
        data=quote,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.HIT,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=0,
    )


def _objects(*, external: bool = False):
    trade_id = uuid4()
    product_id = uuid4()
    position = SimpleNamespace(
        id=uuid4(),
        trade_id=trade_id,
        product_id=product_id,
        open_quantity=100,
        cost_basis=Decimal("200.00"),
    )
    trade = SimpleNamespace(
        id=trade_id,
        workspace_id=uuid4(),
        product_id=product_id,
        product_evaluation_id=None if external else uuid4(),
    )
    listing_id = uuid4()
    evaluation = SimpleNamespace(
        id=trade.product_evaluation_id,
        warrant_id=product_id,
        warrant_listing_id=listing_id,
    )
    listing = SimpleNamespace(
        id=listing_id,
        warrant_id=product_id,
        quotation_currency_code="EUR",
    )
    return position, trade, evaluation, listing


@pytest.mark.asyncio
async def test_values_long_position_at_bid() -> None:
    position, trade, evaluation, listing = _objects()
    service = PositionValuationService(
        database=_Database(
            _Session(
                position=position,
                trade=trade,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        market_data=_Provider(_quote_result(listing.id, bid="2.40", ask="2.45")),
        now=lambda: NOW,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is PositionValuationStatus.OK
    assert result.mark_price_type == "BID"
    assert result.mark_price == Decimal("2.40")
    assert result.market_value == Decimal("240.00")
    assert result.unrealized_gross_pnl == Decimal("40.00")


@pytest.mark.asyncio
async def test_external_trade_without_listing_provenance_is_not_guessed() -> None:
    position, trade, _evaluation, _listing = _objects(external=True)
    service = PositionValuationService(
        database=_Database(_Session(position=position, trade=trade)),
        market_data=None,
        now=lambda: NOW,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is PositionValuationStatus.UNAVAILABLE
    assert result.reason == "NO_HISTORICAL_WARRANT_LISTING_PROVENANCE"
    assert result.market_value is None


@pytest.mark.asyncio
async def test_missing_bid_does_not_estimate_market_value() -> None:
    position, trade, evaluation, listing = _objects()
    service = PositionValuationService(
        database=_Database(
            _Session(
                position=position,
                trade=trade,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        market_data=_Provider(_quote_result(listing.id, bid=None, ask="2.45")),
        now=lambda: NOW,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is PositionValuationStatus.MISSING
    assert result.reason == "WARRANT_BID_MISSING"
    assert result.market_value is None
    assert result.unrealized_gross_pnl is None
