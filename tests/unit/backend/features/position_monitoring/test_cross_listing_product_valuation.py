from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from tests.unit.backend.features.position_monitoring.test_product_valuation import (
    _context,
)
from tests.unit.backend.features.position_monitoring.test_product_valuation import (
    _Session as CurrencySession,
)

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


class _Session(CurrencySession):
    def __init__(
        self,
        *,
        trade,
        position,
        evaluation,
        listing,
        siblings,
        execution_quantity=10,
        execution_price="2.00",
    ):
        super().__init__(
            trade=trade,
            position=position,
            evaluation=evaluation,
            listing=listing,
            execution_quantity=execution_quantity,
            execution_price=execution_price,
        )
        self._siblings = siblings

    async def scalars(self, statement):
        from app.features.product.persistence.models import WarrantListingModel

        if statement.column_descriptions[0]["entity"] is WarrantListingModel:
            return self._siblings
        return await super().scalars(statement)


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
async def test_uses_only_active_quote_listing_and_preserves_historical_provenance() -> None:
    warrant_id = uuid4()
    historical_id = uuid4()
    active_id = uuid4()
    workspace_id = uuid4()
    evaluation_id = uuid4()
    trade, _, _, _ = _context()
    trade.workspace_id = workspace_id
    trade.product_id = warrant_id
    trade.product_evaluation_id = evaluation_id
    position = SimpleNamespace(id=uuid4(), open_quantity=10, cost_basis=Decimal("20.00"))
    evaluation = SimpleNamespace(id=evaluation_id, warrant_listing_id=historical_id)
    historical = SimpleNamespace(
        id=historical_id,
        warrant_id=warrant_id,
        symbol="UNH.XETR",
        quotation_currency_code="EUR",
    )
    active = SimpleNamespace(
        id=active_id,
        warrant_id=warrant_id,
        symbol="VH2LU2.ISSUER",
        quotation_currency_code="EUR",
    )
    provider = _Provider({active_id: _result(active_id, Decimal("2.60"))})
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=historical,
                siblings=[active],
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.AVAILABLE
    assert result.reason == "WARRANT_BID_AVAILABLE_ON_ALTERNATE_LISTING"
    assert result.provenance_listing_id == historical_id
    assert result.quote_listing_id == active_id
    assert result.warrant_listing_id == active_id
    assert result.symbol == "VH2LU2.ISSUER"
    assert result.bid == Decimal("2.60")
    assert result.market_value == Decimal("26.00")
    assert result.unrealized_gross_pnl == Decimal("6.00")
    assert [request.warrant_listing_id for request in provider.requests] == [active_id]
    assert [attempt.warrant_listing_id for attempt in result.source_attempts] == [active_id]
