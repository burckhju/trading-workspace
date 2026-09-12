"""Read-only depot snapshot over existing position, monitoring, and valuation state."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import AlertStatus
from app.features.alert.persistence.models import AlertModel
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)
from app.features.product.persistence.models import WarrantModel
from app.features.trade_plan.persistence.models import (
    TradePlanTargetModel,
    TradePlanVersionModel,
)
from app.features.trade_position.domain.management import TradeManagementStateProjector
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeManagementEventRepository,
)

PositionHealthReader = Callable[[UUID], Awaitable[PositionMonitoringHealth | None]]
ProductValuationReader = Callable[[UUID], Awaitable[ProductPositionValuation | None]]


@dataclass(frozen=True, slots=True)
class PositionOperationalSnapshot:
    trade_id: UUID
    position_id: UUID
    product_name: str
    opened_at: datetime
    open_quantity: int
    average_entry_price: Decimal
    cost_basis: Decimal
    realized_gross_pnl: Decimal
    stop_price: Decimal | None
    target_price: Decimal | None
    monitoring_status: str
    underlying_symbol: str | None
    valuation_status: str
    product_symbol: str | None
    valuation_currency: str | None
    market_value: Decimal | None
    unrealized_gross_pnl: Decimal | None
    open_alert_count: int
    open_alert_types: tuple[str, ...]
    attention_state: str
    target: str
    analysis_warning: str | None = None
    quote_source: str | None = None
    quote_observed_at: datetime | None = None


class OperationalPositionSnapshotService:
    """Compose one non-persisted operational row per open position."""

    _ATTENTION_ORDER: ClassVar[dict[str, int]] = {"ALERT": 0, "DATA_HEALTH": 1, "OK": 2}

    def __init__(
        self,
        session: AsyncSession,
        *,
        health_reader: PositionHealthReader,
        valuation_reader: ProductValuationReader,
    ) -> None:
        self._session = session
        self._health_reader = health_reader
        self._valuation_reader = valuation_reader
        self._management_events = SqlAlchemyTradeManagementEventRepository(session)

    async def list_positions(
        self,
        *,
        workspace_id: UUID,
    ) -> tuple[PositionOperationalSnapshot, ...]:
        rows = (
            await self._session.execute(
                select(PositionModel, TradeModel, WarrantModel)
                .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
                .where(
                    TradeModel.workspace_id == workspace_id,
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                )
                .order_by(PositionModel.opened_at, PositionModel.id)
            )
        ).all()

        snapshots: list[PositionOperationalSnapshot] = []
        for position, trade, warrant in rows:
            stop_price, target_price = await self._current_stop_target(trade)
            alerts = (
                await self._session.scalars(
                    select(AlertModel)
                    .where(
                        AlertModel.trade_id == trade.id,
                        AlertModel.status == AlertStatus.OPEN.value,
                    )
                    .order_by(AlertModel.detected_at, AlertModel.id)
                )
            ).all()
            health = await self._health_reader(trade.id)
            valuation = await self._valuation_reader(trade.id)

            monitoring_status = health.status.value if health is not None else "ERROR"
            valuation_status = valuation.status.value if valuation is not None else "ERROR"
            alert_types = tuple(alert.alert_type for alert in alerts)
            attention_state = self._attention_state(
                alert_types=alert_types,
                monitoring_status=monitoring_status,
                valuation_status=valuation_status,
            )

            snapshots.append(
                PositionOperationalSnapshot(
                    trade_id=trade.id,
                    position_id=position.id,
                    product_name=warrant.display_name,
                    opened_at=position.opened_at,
                    open_quantity=position.open_quantity,
                    average_entry_price=position.average_entry_price,
                    cost_basis=position.cost_basis,
                    realized_gross_pnl=position.realized_gross_pnl,
                    stop_price=stop_price,
                    target_price=target_price,
                    monitoring_status=monitoring_status,
                    underlying_symbol=health.symbol if health is not None else None,
                    valuation_status=valuation_status,
                    product_symbol=valuation.symbol if valuation is not None else None,
                    valuation_currency=valuation.currency if valuation is not None else None,
                    market_value=(
                        valuation.analysis_market_value
                        if valuation is not None and valuation.analysis_usable
                        else (
                            valuation.market_value
                            if valuation is not None
                            and valuation.status
                            in {
                                ProductValuationStatus.AVAILABLE,
                                ProductValuationStatus.LAST_AVAILABLE,
                            }
                            else None
                        )
                    ),
                    unrealized_gross_pnl=(
                        valuation.analysis_unrealized_gross_pnl
                        if valuation is not None and valuation.analysis_usable
                        else (
                            valuation.unrealized_gross_pnl
                            if valuation is not None
                            and valuation.status
                            in {
                                ProductValuationStatus.AVAILABLE,
                                ProductValuationStatus.LAST_AVAILABLE,
                            }
                            else None
                        )
                    ),
                    analysis_warning=valuation.analysis_warning if valuation is not None else None,
                    quote_source=valuation.selected_source if valuation is not None else None,
                    quote_observed_at=(
                        valuation.quote_observed_at if valuation is not None else None
                    ),
                    open_alert_count=len(alert_types),
                    open_alert_types=alert_types,
                    attention_state=attention_state,
                    target=f"/trade-management?trade_id={trade.id}",
                )
            )

        return tuple(
            sorted(
                snapshots,
                key=lambda item: (
                    self._ATTENTION_ORDER[item.attention_state],
                    item.opened_at,
                    str(item.trade_id),
                ),
            )
        )

    async def _current_stop_target(
        self,
        trade: TradeModel,
    ) -> tuple[Decimal | None, Decimal | None]:
        events = await self._management_events.list_effective_for_trade(trade.id)
        management = TradeManagementStateProjector.project(trade_id=trade.id, events=events)
        planned_stop = None
        planned_target = None

        if trade.trade_plan_version_id is not None:
            plan_version = await self._session.scalar(
                select(TradePlanVersionModel).where(
                    TradePlanVersionModel.id == trade.trade_plan_version_id
                )
            )
            if plan_version is not None:
                planned_stop = plan_version.stop_price
                planned_target = await self._session.scalar(
                    select(TradePlanTargetModel.price).where(
                        TradePlanTargetModel.trade_plan_version_id == plan_version.id,
                        TradePlanTargetModel.sequence == 1,
                    )
                )

        return (
            management.stop_price if management.stop_price is not None else planned_stop,
            management.target_price if management.target_price is not None else planned_target,
        )

    @staticmethod
    def _attention_state(
        *,
        alert_types: tuple[str, ...],
        monitoring_status: str,
        valuation_status: str,
    ) -> str:
        if alert_types:
            return "ALERT"
        if monitoring_status != MonitoringHealthStatus.OK.value or valuation_status not in {
            ProductValuationStatus.AVAILABLE.value,
            ProductValuationStatus.LAST_AVAILABLE.value,
        }:
            return "DATA_HEALTH"
        return "OK"
