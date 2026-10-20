"""One current full-exit cohort row per trade, separate from period SELL rows."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.performance.domain.models import (
    CurrencyReference,
    ExecutionSource,
    ExecutionTime,
    ItemStatus,
    PeriodStatus,
    ReportBasis,
    ReportFilters,
    ReportSummary,
)

ClosedTradeGroup = Literal[
    "CANCELLED",
    "HISTORY_UNRESOLVED",
    "OPEN",
    "OUTSIDE_PERIOD",
    "OTHER_CURRENCY",
    "PERIOD_UNRESOLVED",
    "MONETARY_UNRESOLVED",
    "QUALIFIED",
]
TradeClassification = Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


@dataclass(frozen=True, slots=True, kw_only=True)
class ClosedTradeSellContribution(ExecutionTime):
    """A lifetime SELL trace; period attribution does not qualify its money."""

    execution_id: UUID
    quantity: int
    price_per_unit: str | None
    is_closing: bool
    period_status: PeriodStatus
    status: ItemStatus
    reasons: tuple[str, ...]
    currency_code: str | None
    average_cost_per_unit: str | None
    cost_basis_before: str | None
    cost_basis_after: str | None
    realized_gross_pnl_delta: str | None
    realized_gross_pnl_delta_display: str | None
    cost_basis_before_close_reset: str | None
    open_quantity_before: int
    open_quantity_after: int
    currency_confirmation_ids: tuple[UUID, ...]
    cost_basis_execution_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ClosedTradeItem:
    trade_id: UUID
    product_id: UUID
    product_name: str | None
    origin: str
    group: ClosedTradeGroup
    status: ItemStatus
    reasons: tuple[str, ...]
    period_status: PeriodStatus | None
    closing_execution_id: UUID | None
    closing_time: ExecutionTime | None
    currency_code: str | None
    realized_gross_pnl: str | None
    realized_gross_pnl_display: str | None
    classification: TradeClassification | None
    execution_ids: tuple[UUID, ...]
    effective_execution_ids: tuple[UUID, ...]
    currency_confirmation_ids: tuple[UUID, ...]
    sell_contributions: tuple[ClosedTradeSellContribution, ...]


@dataclass(frozen=True, slots=True)
class ClosedTradeCounts:
    """The first eight cohort groups partition all examined trade identities."""

    examined: int
    cancelled: int
    history_unresolved: int
    open: int
    outside_period: int
    other_currency: int
    period_unresolved: int
    monetary_unresolved: int
    qualified: int
    in_period: int
    unresolved: int
    positive: int
    negative: int
    neutral: int


@dataclass(frozen=True, slots=True)
class ClosedTradeReport:
    definition_version: str
    filters: ReportFilters
    interval_start_at: datetime
    interval_end_at: datetime
    basis: ReportBasis
    currency: CurrencyReference
    summary: ReportSummary
    counts: ClosedTradeCounts
    items: tuple[ClosedTradeItem, ...]
    sources: tuple[ExecutionSource, ...]
