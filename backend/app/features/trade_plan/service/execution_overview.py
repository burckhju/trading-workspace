"""Read-only purchase progress, separate from the TradePlan approval lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.features.product.persistence.models import WarrantModel
from app.features.trade_plan.persistence.models import TradePlanVersionModel
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)


class PurchaseStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PlanTradeOverview:
    trade_id: UUID
    trade_plan_version_id: UUID | None
    plan_version: int | None
    product_id: UUID
    product_name: str | None
    product_isin: str | None
    product_wkn: str | None
    status: PurchaseStatus
    open_quantity: int | None
    purchased_on: date | None
    purchased_at: datetime | None
    closed_on: date | None
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PlanExecutionOverview:
    status: PurchaseStatus
    current_version_status: PurchaseStatus
    trades: tuple[PlanTradeOverview, ...]


def _trade_status(
    trade: TradeModel, position: PositionModel | None, has_buy: bool, version: int | None
) -> PurchaseStatus:
    if trade.cancelled_at is not None:
        return PurchaseStatus.CANCELLED
    # A plan approval, selection or empty trade shell is not a recorded purchase.
    # Inconsistent/missing projections must never be labelled "not started".
    if not has_buy or position is None or version is None:
        return PurchaseStatus.UNKNOWN
    if position.open_quantity > 0 and position.closed_at is None:
        return PurchaseStatus.OPEN
    if position.open_quantity == 0 and position.closed_at is not None:
        return PurchaseStatus.CLOSED
    return PurchaseStatus.UNKNOWN


def summarize_status(trades: tuple[PlanTradeOverview, ...]) -> PurchaseStatus:
    if not trades:
        return PurchaseStatus.NOT_STARTED
    states = {trade.status for trade in trades}
    # Never hide an open position because another linked trade was cancelled/closed.
    for state in (PurchaseStatus.OPEN, PurchaseStatus.UNKNOWN, PurchaseStatus.CLOSED):
        if state in states:
            return state
    return PurchaseStatus.CANCELLED


async def read_execution_overviews(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    current_versions: dict[UUID, UUID],
) -> dict[UUID, PlanExecutionOverview]:
    """One set-based read for all plans/versions, using explicit trade provenance only."""
    grouped: dict[UUID, list[PlanTradeOverview]] = {plan_id: [] for plan_id in current_versions}
    if not grouped:
        return {}
    replacement = aliased(ExecutionRecordModel)
    superseded = (
        select(replacement.id)
        .where(replacement.supersedes_execution_id == ExecutionRecordModel.id)
        .correlate(ExecutionRecordModel)
        .exists()
    )
    has_buy = (
        select(ExecutionRecordModel.id)
        .where(
            ExecutionRecordModel.trade_id == TradeModel.id,
            ExecutionRecordModel.product_id == TradeModel.product_id,
            ExecutionRecordModel.side == "BUY",
            ~superseded,
        )
        .correlate(TradeModel)
        .exists()
    )
    rows = (
        await session.execute(
            select(
                TradeModel,
                PositionModel,
                TradePlanVersionModel.version,
                WarrantModel.display_name,
                WarrantModel.isin,
                WarrantModel.wkn,
                has_buy,
            )
            .select_from(TradeModel)
            .outerjoin(
                PositionModel,
                and_(
                    PositionModel.trade_id == TradeModel.id,
                    PositionModel.product_id == TradeModel.product_id,
                ),
            )
            .outerjoin(
                TradePlanVersionModel,
                and_(
                    TradePlanVersionModel.id == TradeModel.trade_plan_version_id,
                    TradePlanVersionModel.trade_plan_id == TradeModel.trade_plan_id,
                ),
            )
            .outerjoin(
                WarrantModel,
                and_(
                    WarrantModel.id == TradeModel.product_id,
                    WarrantModel.workspace_id == TradeModel.workspace_id,
                ),
            )
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.origin == "WORKSPACE_SELECTION",
                TradeModel.trade_plan_id.in_(list(current_versions)),
            )
            .order_by(TradeModel.created_at, TradeModel.id)
        )
    ).all()
    for trade, position, version, name, isin, wkn, bought in rows:
        if trade.trade_plan_id is None:
            continue
        grouped[trade.trade_plan_id].append(
            PlanTradeOverview(
                trade_id=trade.id,
                trade_plan_version_id=trade.trade_plan_version_id,
                plan_version=version,
                product_id=trade.product_id,
                product_name=name,
                product_isin=isin,
                product_wkn=wkn,
                status=_trade_status(trade, position, bought, version),
                open_quantity=position.open_quantity if position and bought else None,
                purchased_on=position.opened_on if position and bought else None,
                purchased_at=position.opened_at if position and bought else None,
                closed_on=position.closed_on if position and bought else None,
                closed_at=position.closed_at if position and bought else None,
            )
        )
    return {
        plan_id: PlanExecutionOverview(
            status=summarize_status(tuple(trades)),
            current_version_status=summarize_status(
                tuple(t for t in trades if t.trade_plan_version_id == current_versions[plan_id])
            ),
            trades=tuple(trades),
        )
        for plan_id, trades in grouped.items()
    }
