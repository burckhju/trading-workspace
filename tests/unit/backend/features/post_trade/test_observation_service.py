"""Unit tests for FT-011 observation application service."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.observation_service import (
    PostTradeListingResolutionError,
    PostTradeNotEligibleError,
    PostTradeObservationExistsError,
    PostTradeObservationService,
)
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    ProductContext,
    TradeExitContext,
)
from app.features.post_trade.domain import (
    PostTradeObservation,
    PostTradeObservationStatus,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.observations = MagicMock()
    uow.observations.get_for_trade = AsyncMock(return_value=None)
    uow.observations.get = AsyncMock()
    uow.observations.add = AsyncMock()
    uow.observations.replace = AsyncMock()
    return uow


def _trade(
    *,
    workspace_id,
    trade_id,
    closed=True,
):
    return TradeExitContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        product_id=uuid4(),
        is_fully_closed=closed,
        full_exit_at=NOW if closed else None,
        realized_gross_pnl=Decimal("10"),
        executions=(),
        management_events=(),
    )


def _observation(
    *,
    workspace_id,
    trade_id,
    observation_id=None,
):
    return PostTradeObservation(
        id=observation_id or uuid4(),
        workspace_id=workspace_id,
        trade_id=trade_id,
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.ACTIVE,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_start_requires_full_exit() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
            closed=False,
        )
    )

    service = PostTradeObservationService(
        uow=_uow(),
        trade_reader=trade_reader,
        planning_reader=MagicMock(),
        product_reader=MagicMock(),
        listing_resolver=MagicMock(),
        market_data_reader=MagicMock(),
        clock=lambda: NOW,
    )

    with pytest.raises(
        PostTradeNotEligibleError,
        match="not fully economically closed",
    ):
        await service.start(
            workspace_id=workspace_id,
            trade_id=trade_id,
            actor_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_start_rejects_existing_observation() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(
        return_value=_observation(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=uuid4(),
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )
    )

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=uuid4())

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=MagicMock(),
        product_reader=product_reader,
        listing_resolver=resolver,
        market_data_reader=MagicMock(),
        clock=lambda: NOW,
    )

    with pytest.raises(PostTradeObservationExistsError):
        await service.start(
            workspace_id=workspace_id,
            trade_id=trade_id,
            actor_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_start_pins_listing_and_persists_observation() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    listing_id = uuid4()
    observation_id = uuid4()
    actor_id = uuid4()

    uow = _uow()

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    product = ProductContext(
        warrant_id=uuid4(),
        underlying_id=uuid4(),
        historical_warrant_terms_version_id=uuid4(),
        maturity_date=date(2026, 12, 18),
        historical_underlying_listing_id=None,
    )

    product_reader = MagicMock()
    product_reader.get = AsyncMock(return_value=product)

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=listing_id)

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=MagicMock(),
        product_reader=product_reader,
        listing_resolver=resolver,
        market_data_reader=MagicMock(),
        clock=lambda: NOW,
        id_factory=lambda: observation_id,
    )

    result = await service.start(
        workspace_id=workspace_id,
        trade_id=trade_id,
        actor_id=actor_id,
    )

    assert result.id == observation_id
    assert result.underlying_listing_id == listing_id
    assert result.status is PostTradeObservationStatus.ACTIVE
    assert result.target_observation_count == 20
    assert result.started_by == actor_id

    uow.observations.add.assert_awaited_once_with(result)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_maps_listing_resolution_failure() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=uuid4(),
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )
    )

    resolver = MagicMock()
    resolver.resolve = AsyncMock(side_effect=LookupError("primary listing missing"))

    service = PostTradeObservationService(
        uow=_uow(),
        trade_reader=trade_reader,
        planning_reader=MagicMock(),
        product_reader=product_reader,
        listing_resolver=resolver,
        market_data_reader=MagicMock(),
        clock=lambda: NOW,
    )

    with pytest.raises(
        PostTradeListingResolutionError,
        match="primary listing missing",
    ):
        await service.start(
            workspace_id=workspace_id,
            trade_id=trade_id,
            actor_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_refresh_keeps_active_before_twenty_points() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(
        return_value=PlanningContext(
            trade_plan_id=None,
            trade_plan_version_id=None,
            original_stop=None,
            original_targets=(),
        )
    )

    market = MagicMock()
    market.list_range = AsyncMock(
        return_value=(
            DailyObservation(
                listing_id=observation.underlying_listing_id,
                trading_date=date(2026, 8, 19),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("90"),
                close=Decimal("105"),
                adjusted_close=None,
                quality_status="VALID",
            ),
        )
    )

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=MagicMock(),
        listing_resolver=MagicMock(),
        market_data_reader=market,
        clock=lambda: NOW + timedelta(days=5),
    )

    updated, evidence = await service.refresh(
        workspace_id=workspace_id,
        observation_id=observation.id,
    )

    assert updated.status is PostTradeObservationStatus.ACTIVE
    assert evidence.available_observation_count == 1
    assert evidence.horizon_complete is False
    uow.observations.replace.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_completes_at_twenty_points() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(
        return_value=PlanningContext(
            trade_plan_id=uuid4(),
            trade_plan_version_id=uuid4(),
            original_stop=Decimal("90"),
            original_targets=(Decimal("110"),),
        )
    )

    prices = tuple(
        DailyObservation(
            listing_id=observation.underlying_listing_id,
            trading_date=date(2026, 8, 19) + timedelta(days=i),
            open=Decimal("100"),
            high=Decimal("115"),
            low=Decimal("85"),
            close=Decimal("105"),
            adjusted_close=None,
            quality_status="VALID",
        )
        for i in range(20)
    )

    market = MagicMock()
    market.list_range = AsyncMock(return_value=prices)

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=MagicMock(),
        listing_resolver=MagicMock(),
        market_data_reader=market,
        clock=lambda: NOW + timedelta(days=40),
    )

    updated, evidence = await service.refresh(
        workspace_id=workspace_id,
        observation_id=observation.id,
    )

    assert evidence.horizon_complete is True
    assert updated.status is PostTradeObservationStatus.COMPLETED
    assert updated.completed_at is not None
    uow.observations.replace.assert_awaited_once_with(updated)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_uses_pinned_listing() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(
        return_value=PlanningContext(
            trade_plan_id=None,
            trade_plan_version_id=None,
            original_stop=None,
            original_targets=(),
        )
    )

    market = MagicMock()
    market.list_range = AsyncMock(return_value=())

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=MagicMock(),
        listing_resolver=MagicMock(),
        market_data_reader=market,
        clock=lambda: NOW + timedelta(days=1),
    )

    await service.refresh(
        workspace_id=workspace_id,
        observation_id=observation.id,
    )

    market.list_range.assert_awaited_once()
    kwargs = market.list_range.await_args.kwargs
    assert kwargs["listing_id"] == observation.underlying_listing_id
