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

NOW = datetime(2026, 9, 11, 15, 0, tzinfo=UTC)


class _ExecuteResult:
    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *, trade, position, evaluation, listing, siblings):
        self._trade = trade
        self._position = position
        self._scalars = [evaluation, listing]
        self._siblings = siblings

    async def execute(self, _statement):
        return _ExecuteResult((self._trade, self._position))

    async def scalar(self, _statement):
        return self._scalars.pop(0)

    async def scalars(self, _statement):
        return self._siblings


class _Database:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def session_context(self):
        yield self._session


class _Provider:
    def __init__(self, results):
        self._results = results
        self.requests = []

    async def get_warrant_listing_quote(self, request):
        self.requests.append(request)
        return self._results[request.warrant_listing_id]


def _result(listing_id, bid):
    quote = None
    if bid is not None:
        quote = WarrantQuoteSnapshot(
            warrant_listing_id=listing_id,
            bid=bid,
            ask=bid + Decimal("0.05"),
            currency="EUR",
            provider_symbol="TEST",
            provider_exchange_code="MUND",
            observed_at=NOW,
        )
    return MarketDataResult(
        data=quote,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.BYPASS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=None,
    )


@pytest.mark.asyncio
async def test_uses_active_alternate_listing_for_same_warrant_when_primary_has_no_quote() -> None:
    warrant_id = uuid4()
    primary_id = uuid4()
    alternate_id = uuid4()
    workspace_id = uuid4()
    evaluation_id = uuid4()
    trade = SimpleNamespace(
        id=uuid4(), workspace_id=workspace_id, product_evaluation_id=evaluation_id
    )
    position = SimpleNamespace(id=uuid4(), open_quantity=10, cost_basis=Decimal("20.00"))
    evaluation = SimpleNamespace(id=evaluation_id, warrant_listing_id=primary_id)
    primary = SimpleNamespace(
        id=primary_id,
        warrant_id=warrant_id,
        symbol="TEST.STU",
        quotation_currency_code="EUR",
    )
    alternate = SimpleNamespace(
        id=alternate_id,
        warrant_id=warrant_id,
        symbol="TEST.GETTEX",
        quotation_currency_code="EUR",
    )
    provider = _Provider(
        {
            primary_id: _result(primary_id, None),
            alternate_id: _result(alternate_id, Decimal("2.60")),
        }
    )
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=primary,
                siblings=[primary, alternate],
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.AVAILABLE
    assert result.reason == "WARRANT_BID_AVAILABLE_ON_ALTERNATE_LISTING"
    assert result.warrant_listing_id == alternate_id
    assert result.symbol == "TEST.GETTEX"
    assert result.bid == Decimal("2.60")
    assert result.market_value == Decimal("26.00")
    assert result.unrealized_gross_pnl == Decimal("6.00")
    assert [attempt.warrant_listing_id for attempt in result.source_attempts] == [
        primary_id,
        alternate_id,
    ]
