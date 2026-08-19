"""Unit tests for FT-011 concrete cross-feature read adapters."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.market.persistence.enums import LifecycleStatus
from app.features.post_trade.application.ports import ProductContext
from app.features.post_trade.application.read_adapters import (
    SqlAlchemyHistoricalPlanningContextReader,
    SqlAlchemyHistoricalProductContextReader,
    SqlAlchemyObservationMarketDataReader,
    SqlAlchemyTradeExitContextReader,
    SqlAlchemyUnderlyingListingResolver,
)
from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
    TradeManagementEvent,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_trade_exit_context_uses_effective_sell_and_position_state() -> None:
    reader = object.__new__(SqlAlchemyTradeExitContextReader)

    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )

    position = Position(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        open_quantity=0,
        cost_basis=Decimal("0"),
        average_entry_price=Decimal("10"),
        opened_at=NOW,
        last_execution_at=NOW,
        realized_gross_pnl=Decimal("125.50"),
        closed_at=NOW,
    )

    buy = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=10,
        price_per_unit=Decimal("10"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        side=ExecutionSide.BUY,
    )

    sell = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=10,
        price_per_unit=Decimal("22.55"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        side=ExecutionSide.SELL,
    )

    event = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade.id,
        event_type=TradeManagementEventType.STOP_CHANGED,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        numeric_value=Decimal("9.50"),
    )

    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(return_value=trade)
    reader._positions = MagicMock()
    reader._positions.get_for_trade = AsyncMock(return_value=position)
    reader._executions = MagicMock()
    reader._executions.list_effective_for_trade = AsyncMock(return_value=[buy, sell])
    reader._management_events = MagicMock()
    reader._management_events.list_effective_for_trade = AsyncMock(return_value=[event])

    result = await reader.get(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
    )

    assert result is not None
    assert result.is_fully_closed is True
    assert result.full_exit_at == NOW
    assert result.realized_gross_pnl == Decimal("125.50")
    assert len(result.executions) == 1
    assert result.executions[0].execution_id == sell.id
    assert result.executions[0].quantity == 10
    assert len(result.management_events) == 1
    assert result.management_events[0].kind == "STOP_CHANGED"


@pytest.mark.asyncio
async def test_trade_exit_context_returns_none_when_trade_missing() -> None:
    reader = object.__new__(SqlAlchemyTradeExitContextReader)
    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(return_value=None)

    assert (
        await reader.get(
            workspace_id=uuid4(),
            trade_id=uuid4(),
        )
        is None
    )


@pytest.mark.asyncio
async def test_planning_context_reads_historical_plan_version() -> None:
    reader = object.__new__(SqlAlchemyHistoricalPlanningContextReader)

    plan_id = uuid4()
    version_id = uuid4()
    trade = SimpleNamespace(
        trade_plan_id=plan_id,
        trade_plan_version_id=version_id,
    )

    version = SimpleNamespace(
        id=version_id,
        invalidation=SimpleNamespace(stop_price=Decimal("95.00")),
        targets=(
            SimpleNamespace(price=Decimal("110.00")),
            SimpleNamespace(price=Decimal("120.00")),
        ),
    )

    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(return_value=trade)
    reader._versions = MagicMock()
    reader._versions.get = AsyncMock(return_value=version)

    result = await reader.get(
        workspace_id=uuid4(),
        trade_id=uuid4(),
    )

    assert result.trade_plan_id == plan_id
    assert result.trade_plan_version_id == version_id
    assert result.original_stop == Decimal("95.00")
    assert result.original_targets == (
        Decimal("110.00"),
        Decimal("120.00"),
    )


@pytest.mark.asyncio
async def test_planning_context_for_external_trade_is_empty() -> None:
    reader = object.__new__(SqlAlchemyHistoricalPlanningContextReader)
    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(
        return_value=SimpleNamespace(
            trade_plan_id=None,
            trade_plan_version_id=None,
        )
    )

    result = await reader.get(
        workspace_id=uuid4(),
        trade_id=uuid4(),
    )

    assert result.trade_plan_id is None
    assert result.trade_plan_version_id is None
    assert result.original_stop is None
    assert result.original_targets == ()


@pytest.mark.asyncio
async def test_product_context_uses_historical_evaluation_and_terms() -> None:
    reader = object.__new__(SqlAlchemyHistoricalProductContextReader)

    workspace_id = uuid4()
    trade_id = uuid4()
    evaluation_id = uuid4()
    warrant_id = uuid4()
    terms_id = uuid4()
    underlying_id = uuid4()

    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(
        return_value=SimpleNamespace(
            product_id=warrant_id,
            product_evaluation_id=evaluation_id,
        )
    )

    evaluation = SimpleNamespace(
        warrant_id=warrant_id,
        warrant_terms_version_id=terms_id,
        warrant_listing_id=uuid4(),
    )

    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
    )

    terms = SimpleNamespace(
        id=terms_id,
        warrant_id=warrant_id,
        maturity_date=date(2026, 12, 18),
    )

    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[evaluation, warrant, terms])
    reader._session = session

    result = await reader.get(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    assert result is not None
    assert result.warrant_id == warrant_id
    assert result.underlying_id == underlying_id
    assert result.historical_warrant_terms_version_id == terms_id
    assert result.maturity_date == date(2026, 12, 18)


@pytest.mark.asyncio
async def test_external_product_context_does_not_invent_terms() -> None:
    reader = object.__new__(SqlAlchemyHistoricalProductContextReader)

    workspace_id = uuid4()
    warrant_id = uuid4()
    underlying_id = uuid4()

    reader._trades = MagicMock()
    reader._trades.get = AsyncMock(
        return_value=SimpleNamespace(
            product_id=warrant_id,
            product_evaluation_id=None,
        )
    )

    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
    )

    session = MagicMock()
    session.scalar = AsyncMock(return_value=warrant)
    reader._session = session

    result = await reader.get(
        workspace_id=workspace_id,
        trade_id=uuid4(),
    )

    assert result is not None
    assert result.warrant_id == warrant_id
    assert result.underlying_id == underlying_id
    assert result.historical_warrant_terms_version_id is None
    assert result.maturity_date is None


@pytest.mark.asyncio
async def test_listing_resolver_uses_single_active_primary_listing() -> None:
    reader = object.__new__(SqlAlchemyUnderlyingListingResolver)

    listing_id = uuid4()
    product = ProductContext(
        warrant_id=uuid4(),
        underlying_id=uuid4(),
        historical_warrant_terms_version_id=None,
        maturity_date=None,
        historical_underlying_listing_id=None,
    )

    listing = SimpleNamespace(
        id=listing_id,
        underlying_id=product.underlying_id,
        lifecycle_status=LifecycleStatus.ACTIVE,
        is_primary=True,
    )

    reader._listings = MagicMock()
    reader._listings.list_for_underlying = AsyncMock(return_value=[listing])

    result = await reader.resolve(
        workspace_id=uuid4(),
        product_context=product,
        observation_started_at=NOW,
    )

    assert result == listing_id


@pytest.mark.asyncio
async def test_listing_resolver_rejects_multiple_active_primary_listings() -> None:
    reader = object.__new__(SqlAlchemyUnderlyingListingResolver)

    product = ProductContext(
        warrant_id=uuid4(),
        underlying_id=uuid4(),
        historical_warrant_terms_version_id=None,
        maturity_date=None,
        historical_underlying_listing_id=None,
    )

    reader._listings = MagicMock()
    reader._listings.list_for_underlying = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=uuid4(),
                underlying_id=product.underlying_id,
                lifecycle_status=LifecycleStatus.ACTIVE,
                is_primary=True,
            ),
            SimpleNamespace(
                id=uuid4(),
                underlying_id=product.underlying_id,
                lifecycle_status=LifecycleStatus.ACTIVE,
                is_primary=True,
            ),
        ]
    )

    with pytest.raises(
        ValueError,
        match="multiple active primary underlying listings",
    ):
        await reader.resolve(
            workspace_id=uuid4(),
            product_context=product,
            observation_started_at=NOW,
        )


@pytest.mark.asyncio
async def test_listing_resolver_rejects_missing_primary_listing() -> None:
    reader = object.__new__(SqlAlchemyUnderlyingListingResolver)

    product = ProductContext(
        warrant_id=uuid4(),
        underlying_id=uuid4(),
        historical_warrant_terms_version_id=None,
        maturity_date=None,
        historical_underlying_listing_id=None,
    )

    reader._listings = MagicMock()
    reader._listings.list_for_underlying = AsyncMock(return_value=[])

    with pytest.raises(
        LookupError,
        match="underlying primary listing is not resolvable",
    ):
        await reader.resolve(
            workspace_id=uuid4(),
            product_context=product,
            observation_started_at=NOW,
        )


@pytest.mark.asyncio
async def test_market_data_reader_maps_daily_price_rows() -> None:
    reader = object.__new__(SqlAlchemyObservationMarketDataReader)

    listing_id = uuid4()
    row = SimpleNamespace(
        listing_id=listing_id,
        trading_date=date(2026, 8, 19),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        adjusted_close=Decimal("104"),
        volume=Decimal("1000"),
        currency="EUR",
        provider=SimpleNamespace(value="EODHD"),
        provider_symbol="TEST",
        retrieved_at=NOW,
        source_updated_at=None,
        quality_status=SimpleNamespace(value="COMPLETE"),
        warnings="",
        price_type=SimpleNamespace(value="EOD"),
    )

    reader._prices = MagicMock()
    reader._prices.list_range = AsyncMock(return_value=[row])

    # Patch the mapping boundary by giving the row enum-like objects expected
    # by daily_price_to_domain.
    from app.features.market_data.domain.enums import (
        MarketDataProvider,
        PriceType,
        QualityStatus,
    )

    row.provider = MarketDataProvider.EODHD
    quality_status = next(
        (value for value in QualityStatus if value is not QualityStatus.INCOMPLETE),
        QualityStatus.INCOMPLETE,
    )
    row.quality_status = quality_status
    row.price_type = PriceType.EOD

    result = await reader.list_range(
        workspace_id=uuid4(),
        listing_id=listing_id,
        start_date=date(2026, 8, 19),
        end_date=date(2026, 8, 20),
    )

    assert len(result) == 1
    assert result[0].listing_id == listing_id
    assert result[0].trading_date == date(2026, 8, 19)
    assert result[0].high == Decimal("110")
    assert result[0].low == Decimal("95")
    assert result[0].close == Decimal("105")
    assert result[0].quality_status == quality_status.value
