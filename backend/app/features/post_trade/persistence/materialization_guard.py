"""PostgreSQL source stability for a short, explicit FT-011 evidence handoff.

Locks do not write or reinterpret sources. Parent FOR UPDATE locks exclude child
inserts through the existing FKs; existing children are locked too, including all
prices for the pinned listing so date changes/backfills cannot evade a range lock.
NOWAIT avoids waiting in a foreign owner's lock order. The enclosing FT-012 UOW
must keep this *same session* open through evidence commit/rollback.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import ListingModel
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.post_trade.application.materialization_handoff import Ft011SourceBusyError
from app.features.post_trade.persistence.models import (
    ExitReviewModel,
    ExitReviewVersionModel,
    PostTradeObservationModel,
)
from app.features.trade_plan.persistence.models import TradePlanTargetModel, TradePlanVersionModel
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeManagementEventModel,
    TradeModel,
)


class SqlAlchemyMaterializationSourceGuard:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lock(self, statement: Select[Any]) -> None:
        await self._session.execute(
            statement.with_for_update(nowait=True).execution_options(populate_existing=True)
        )

    async def acquire(self, *, workspace_id: UUID, trade_id: UUID) -> None:
        try:
            await self._acquire(workspace_id, trade_id)
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
            if code not in {"55P03", "40P01", "40001"}:
                raise
            raise Ft011SourceBusyError("FT-011 source is being changed; retry explicitly") from exc

    async def _acquire(self, workspace_id: UUID, trade_id: UUID) -> None:
        trade = await self._session.scalar(
            select(TradeModel)
            .where(TradeModel.workspace_id == workspace_id, TradeModel.id == trade_id)
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        )
        if trade is None:
            return  # The FT-011 gate/inspector, not this lock adapter, decides eligibility.
        for model in (ExecutionRecordModel, PositionModel, TradeManagementEventModel):
            await self._lock(select(model).where(model.trade_id == trade_id).order_by(model.id))
        observation = await self._session.scalar(
            select(PostTradeObservationModel)
            .where(
                PostTradeObservationModel.workspace_id == workspace_id,
                PostTradeObservationModel.trade_id == trade_id,
            )
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        )
        if observation is None:
            return
        review = await self._session.scalar(
            select(ExitReviewModel)
            .where(
                ExitReviewModel.workspace_id == workspace_id,
                ExitReviewModel.post_trade_observation_id == observation.id,
            )
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        )
        if review is not None:
            await self._lock(
                select(ExitReviewVersionModel)
                .where(ExitReviewVersionModel.exit_review_id == review.id)
                .order_by(ExitReviewVersionModel.id)
            )
        if trade.trade_plan_version_id is not None:
            await self._lock(
                select(TradePlanVersionModel).where(
                    TradePlanVersionModel.id == trade.trade_plan_version_id,
                    TradePlanVersionModel.trade_plan_id == trade.trade_plan_id,
                )
            )
            await self._lock(
                select(TradePlanTargetModel)
                .where(TradePlanTargetModel.trade_plan_version_id == trade.trade_plan_version_id)
                .order_by(TradePlanTargetModel.id)
            )
        await self._lock(
            select(ListingModel).where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.id == observation.underlying_listing_id,
            )
        )
        await self._lock(
            select(DailyPriceModel)
            .where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.listing_id == observation.underlying_listing_id,
            )
            .order_by(DailyPriceModel.id)
        )
