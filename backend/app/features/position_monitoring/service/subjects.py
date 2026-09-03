from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel
from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.position_monitoring.domain.models import MonitoringRule, MonitoringRuleType
from app.features.product.persistence.models import WarrantModel
from app.features.trade_plan.persistence.models import (
    TradePlanModel,
    TradePlanTargetModel,
    TradePlanVersionModel,
)
from app.features.trade_position.domain.management import TradeManagementStateProjector
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeManagementEventRepository,
)


class SubjectResolutionIssue(StrEnum):
    NO_RULES = "NO_RULES"
    NO_PRIMARY_LISTING = "NO_PRIMARY_LISTING"
    NO_ACTIVE_MAPPING = "NO_ACTIVE_MAPPING"
    PLAN_UNDERLYING_MISMATCH = "PLAN_UNDERLYING_MISMATCH"
    PLAN_VERSION_MISSING = "PLAN_VERSION_MISSING"


@dataclass(frozen=True, slots=True)
class MonitoringSubject:
    workspace_id: UUID
    position_id: UUID
    trade_id: UUID
    listing_id: UUID
    mapping_id: UUID
    symbol: str
    rules: tuple[MonitoringRule, ...]


@dataclass(frozen=True, slots=True)
class MonitoringSubjectResolution:
    position_id: UUID
    subject: MonitoringSubject | None
    issue: SubjectResolutionIssue | None = None


class SqlAlchemyMonitoringSubjectReader:
    """Resolve open positions to current management rules and market-data addresses."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._management_events = SqlAlchemyTradeManagementEventRepository(session)

    async def list_resolutions(self) -> tuple[MonitoringSubjectResolution, ...]:
        rows = (
            await self._session.execute(
                select(PositionModel, TradeModel, WarrantModel)
                .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                .join(WarrantModel, WarrantModel.id == TradeModel.product_id)
                .where(PositionModel.open_quantity > 0, PositionModel.closed_at.is_(None))
                .order_by(PositionModel.id)
            )
        ).all()
        return tuple([await self._resolve(position, trade, warrant) for position, trade, warrant in rows])

    async def _resolve(
        self,
        position: PositionModel,
        trade: TradeModel,
        warrant: WarrantModel,
    ) -> MonitoringSubjectResolution:
        events = await self._management_events.list_effective_for_trade(trade.id)
        management = TradeManagementStateProjector.project(trade_id=trade.id, events=events)
        planned_stop = None
        planned_target = None

        if trade.trade_plan_version_id is not None:
            plan_row = (
                await self._session.execute(
                    select(TradePlanVersionModel, TradePlanModel)
                    .join(TradePlanModel, TradePlanModel.id == TradePlanVersionModel.trade_plan_id)
                    .where(
                        TradePlanVersionModel.id == trade.trade_plan_version_id,
                        TradePlanModel.id == trade.trade_plan_id,
                    )
                )
            ).first()
            if plan_row is None:
                return MonitoringSubjectResolution(
                    position_id=position.id,
                    subject=None,
                    issue=SubjectResolutionIssue.PLAN_VERSION_MISSING,
                )
            plan_version, plan = plan_row
            if plan.underlying_id != warrant.underlying_id:
                return MonitoringSubjectResolution(
                    position_id=position.id,
                    subject=None,
                    issue=SubjectResolutionIssue.PLAN_UNDERLYING_MISMATCH,
                )
            planned_stop = plan_version.stop_price
            planned_target = await self._session.scalar(
                select(TradePlanTargetModel.price).where(
                    TradePlanTargetModel.trade_plan_version_id == plan_version.id,
                    TradePlanTargetModel.sequence == 1,
                )
            )

        rules: list[MonitoringRule] = []
        stop = management.stop_price if management.stop_price is not None else planned_stop
        target = management.target_price if management.target_price is not None else planned_target
        if stop is not None:
            rules.append(MonitoringRule("CURRENT_STOP", MonitoringRuleType.STOP_REACHED, stop))
        if target is not None:
            rules.append(MonitoringRule("CURRENT_TARGET", MonitoringRuleType.TARGET_REACHED, target))
        if not rules:
            return MonitoringSubjectResolution(
                position_id=position.id,
                subject=None,
                issue=SubjectResolutionIssue.NO_RULES,
            )

        listing = await self._session.scalar(
            select(ListingModel).where(
                ListingModel.workspace_id == trade.workspace_id,
                ListingModel.underlying_id == warrant.underlying_id,
                ListingModel.is_primary.is_(True),
                ListingModel.lifecycle_status == LifecycleStatus.ACTIVE,
            )
        )
        if listing is None:
            return MonitoringSubjectResolution(
                position_id=position.id,
                subject=None,
                issue=SubjectResolutionIssue.NO_PRIMARY_LISTING,
            )
        mapping = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == trade.workspace_id,
                ProviderInstrumentMappingModel.listing_id == listing.id,
                ProviderInstrumentMappingModel.status == MappingStatus.ACTIVE,
            )
        )
        if mapping is None:
            return MonitoringSubjectResolution(
                position_id=position.id,
                subject=None,
                issue=SubjectResolutionIssue.NO_ACTIVE_MAPPING,
            )
        return MonitoringSubjectResolution(
            position_id=position.id,
            subject=MonitoringSubject(
                workspace_id=trade.workspace_id,
                position_id=position.id,
                trade_id=trade.id,
                listing_id=listing.id,
                mapping_id=mapping.id,
                symbol=listing.ticker,
                rules=tuple(rules),
            ),
        )
