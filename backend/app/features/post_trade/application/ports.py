"""Read-side ports consumed by FT-011 Post Trade."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExitExecutionFact:
    execution_id: UUID
    quantity: Decimal
    price_per_unit: Decimal
    executed_at: datetime


@dataclass(frozen=True, slots=True)
class ManagementLevelFact:
    event_id: UUID
    kind: str
    effective_at: datetime
    numeric_value: Decimal | None


@dataclass(frozen=True, slots=True)
class TradeExitContext:
    workspace_id: UUID
    trade_id: UUID
    product_id: UUID
    is_fully_closed: bool
    full_exit_at: datetime | None
    realized_gross_pnl: Decimal
    executions: tuple[ExitExecutionFact, ...]
    management_events: tuple[ManagementLevelFact, ...]


@dataclass(frozen=True, slots=True)
class PlanningContext:
    trade_plan_id: UUID | None
    trade_plan_version_id: UUID | None
    original_stop: Decimal | None
    original_targets: tuple[Decimal, ...]


@dataclass(frozen=True, slots=True)
class ProductContext:
    warrant_id: UUID
    underlying_id: UUID
    historical_warrant_terms_version_id: UUID | None
    maturity_date: date | None
    historical_underlying_listing_id: UUID | None


@dataclass(frozen=True, slots=True)
class DailyObservation:
    listing_id: UUID
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    quality_status: str | None


class TradeExitContextReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> TradeExitContext | None: ...


class HistoricalPlanningContextReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> PlanningContext: ...


class HistoricalProductContextReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> ProductContext | None: ...


class UnderlyingListingResolver(Protocol):
    async def resolve(
        self,
        *,
        workspace_id: UUID,
        product_context: ProductContext,
        observation_started_at: datetime,
    ) -> UUID: ...


class ObservationMarketDataReader(Protocol):
    async def list_range(
        self,
        *,
        workspace_id: UUID,
        listing_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Sequence[DailyObservation]: ...
