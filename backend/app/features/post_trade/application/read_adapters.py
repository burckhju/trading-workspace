"""SQLAlchemy read adapters for FT-011 cross-feature facts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.enums import LifecycleStatus
from app.features.market.persistence.repositories import (
    SqlAlchemyListingRepository,
)
from app.features.market_data.persistence.mapping import daily_price_to_domain
from app.features.market_data.persistence.repositories import (
    SqlAlchemyDailyPriceRepository,
)
from app.features.post_trade.application.ports import (
    DailyObservation,
    ExitExecutionFact,
    ManagementLevelFact,
    PlanningContext,
    ProductContext,
    TradeExitContext,
)
from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product_selection.persistence.models import (
    ProductEvaluationModel,
)
from app.features.trade_plan.persistence.repositories import (
    SqlAlchemyTradePlanRepository,
    SqlAlchemyTradePlanVersionRepository,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyTradeManagementEventRepository,
    SqlAlchemyTradeRepository,
)


class SqlAlchemyTradeExitContextReader:
    def __init__(self, session: AsyncSession) -> None:
        self._trades = SqlAlchemyTradeRepository(session)
        self._executions = SqlAlchemyExecutionRecordRepository(session)
        self._positions = SqlAlchemyPositionRepository(session)
        self._management_events = SqlAlchemyTradeManagementEventRepository(session)

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> TradeExitContext | None:
        trade = await self._trades.get(workspace_id, trade_id)
        if trade is None:
            return None

        position = await self._positions.get_for_trade(
            workspace_id,
            trade_id,
        )
        if position is None:
            return None

        executions = await self._executions.list_effective_for_trade(trade_id)
        management = await self._management_events.list_effective_for_trade(trade_id)

        exit_executions = tuple(
            ExitExecutionFact(
                execution_id=value.id,
                quantity=Decimal(value.quantity),
                price_per_unit=value.price_per_unit,
                executed_at=value.executed_at,
            )
            for value in executions
            if value.side is ExecutionSide.SELL
        )

        management_events = tuple(
            ManagementLevelFact(
                event_id=value.id,
                kind=value.event_type.value,
                effective_at=value.effective_at,
                numeric_value=value.numeric_value,
            )
            for value in management
        )

        return TradeExitContext(
            workspace_id=workspace_id,
            trade_id=trade.id,
            product_id=trade.product_id,
            is_fully_closed=position.is_closed,
            full_exit_at=position.closed_at,
            realized_gross_pnl=position.realized_gross_pnl,
            executions=exit_executions,
            management_events=management_events,
        )


class SqlAlchemyHistoricalPlanningContextReader:
    def __init__(self, session: AsyncSession) -> None:
        self._trades = SqlAlchemyTradeRepository(session)
        self._plans = SqlAlchemyTradePlanRepository(session)
        self._versions = SqlAlchemyTradePlanVersionRepository(
            session,
            self._plans,
        )

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> PlanningContext:
        trade = await self._trades.get(workspace_id, trade_id)

        if trade is None or trade.trade_plan_id is None or trade.trade_plan_version_id is None:
            return PlanningContext(
                trade_plan_id=None,
                trade_plan_version_id=None,
                original_stop=None,
                original_targets=(),
            )

        version = await self._versions.get(
            trade.trade_plan_id,
            trade.trade_plan_version_id,
        )
        if version is None:
            return PlanningContext(
                trade_plan_id=trade.trade_plan_id,
                trade_plan_version_id=trade.trade_plan_version_id,
                original_stop=None,
                original_targets=(),
            )

        return PlanningContext(
            trade_plan_id=trade.trade_plan_id,
            trade_plan_version_id=version.id,
            original_stop=version.invalidation.stop_price,
            original_targets=tuple(target.price for target in version.targets),
        )


class SqlAlchemyHistoricalProductContextReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trades = SqlAlchemyTradeRepository(session)

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> ProductContext | None:
        trade = await self._trades.get(workspace_id, trade_id)
        if trade is None:
            return None

        if trade.product_evaluation_id is None:
            return await self._external_trade_context(
                workspace_id=workspace_id,
                warrant_id=trade.product_id,
            )

        evaluation = await self._session.scalar(
            select(ProductEvaluationModel).where(
                ProductEvaluationModel.id == trade.product_evaluation_id,
            )
        )
        if evaluation is None:
            return None

        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.id == evaluation.warrant_id,
                WarrantModel.workspace_id == workspace_id,
            )
        )
        if warrant is None:
            return None

        terms = await self._session.scalar(
            select(WarrantTermsVersionModel).where(
                WarrantTermsVersionModel.id == evaluation.warrant_terms_version_id,
                WarrantTermsVersionModel.warrant_id == evaluation.warrant_id,
            )
        )
        if terms is None:
            return None

        return ProductContext(
            warrant_id=warrant.id,
            underlying_id=warrant.underlying_id,
            historical_warrant_terms_version_id=terms.id,
            maturity_date=terms.maturity_date,
            historical_underlying_listing_id=None,
        )

    async def _external_trade_context(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
    ) -> ProductContext | None:
        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.id == warrant_id,
                WarrantModel.workspace_id == workspace_id,
            )
        )
        if warrant is None:
            return None

        return ProductContext(
            warrant_id=warrant.id,
            underlying_id=warrant.underlying_id,
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )


class SqlAlchemyUnderlyingListingResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._listings = SqlAlchemyListingRepository(session)

    async def resolve(
        self,
        *,
        workspace_id: UUID,
        product_context: ProductContext,
        observation_started_at: datetime,
    ) -> UUID:
        del observation_started_at

        if product_context.historical_underlying_listing_id is not None:
            listing = await self._listings.get(
                workspace_id,
                product_context.historical_underlying_listing_id,
            )
            if listing is None or listing.underlying_id != product_context.underlying_id:
                raise LookupError("historical underlying listing is not resolvable")
            return listing.id

        listings = await self._listings.list_for_underlying(
            workspace_id,
            product_context.underlying_id,
        )

        active_primary = [
            listing
            for listing in listings
            if listing.lifecycle_status is LifecycleStatus.ACTIVE and listing.is_primary
        ]

        if not active_primary:
            raise LookupError("underlying primary listing is not resolvable")

        if len(active_primary) > 1:
            raise ValueError("multiple active primary underlying listings")

        return active_primary[0].id


class SqlAlchemyObservationMarketDataReader:
    def __init__(self, session: AsyncSession) -> None:
        self._prices = SqlAlchemyDailyPriceRepository(session)

    async def list_range(
        self,
        *,
        workspace_id: UUID,
        listing_id: UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[DailyObservation, ...]:
        rows = await self._prices.list_range(
            workspace_id,
            listing_id,
            start_date,
            end_date,
        )

        values = []
        for row in rows:
            price = daily_price_to_domain(row)
            values.append(
                DailyObservation(
                    listing_id=price.listing_id,
                    trading_date=price.trading_date,
                    open=price.open,
                    high=price.high,
                    low=price.low,
                    close=price.close,
                    adjusted_close=price.adjusted_close,
                    quality_status=price.quality_status.value,
                )
            )

        return tuple(values)
