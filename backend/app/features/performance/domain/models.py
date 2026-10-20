"""Immutable report inputs and response values, with money represented as strings."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord, Trade

PeriodStatus = Literal["IN_PERIOD", "OUTSIDE_PERIOD", "PERIOD_AMBIGUOUS", "PERIOD_UNKNOWN"]
ItemStatus = Literal["USABLE", "NOT_COMPUTABLE", "EXCLUDED"]
SummaryStatus = Literal["EMPTY", "COMPLETE", "PARTIAL", "NOT_COMPUTABLE"]


@dataclass(frozen=True, slots=True)
class ReportFilters:
    from_date: date
    to_date: date
    report_currency: str
    report_timezone: str


@dataclass(frozen=True, slots=True)
class CurrencyReference:
    code: str
    minor_unit: int
    reference_version: str
    rounding: Literal["ROUND_HALF_EVEN"] = "ROUND_HALF_EVEN"


@dataclass(frozen=True, slots=True)
class Confirmation:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    execution_id: UUID
    currency_code: str
    source: str
    note: str | None
    confirmed_at: datetime
    confirmed_by: UUID
    supersedes_confirmation_id: UUID | None
    request_id: UUID | None


@dataclass(frozen=True, slots=True)
class ExecutionFact:
    id: UUID
    trade_id: UUID
    product_id: UUID
    side: str
    quantity: int
    price_per_unit: Decimal
    executed_at: datetime
    recorded_at: datetime
    recorded_by: UUID
    supersedes_execution_id: UUID | None
    executed_on: date | None
    execution_timezone: str | None

    def to_domain(self) -> ExecutionRecord:
        if not self.price_per_unit.is_finite():
            raise ValueError("Execution price is not finite")
        return ExecutionRecord(
            id=self.id,
            trade_id=self.trade_id,
            product_id=self.product_id,
            side=ExecutionSide(self.side),
            quantity=self.quantity,
            price_per_unit=self.price_per_unit,
            executed_at=self.executed_at,
            recorded_at=self.recorded_at,
            recorded_by=self.recorded_by,
            supersedes_execution_id=self.supersedes_execution_id,
            executed_on=self.executed_on,
            execution_timezone=self.execution_timezone,
        )


@dataclass(frozen=True, slots=True)
class TradeFact:
    trade: Trade
    product_name: str | None
    position_id: UUID | None


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    workspace_id: UUID
    trades: tuple[TradeFact, ...]
    executions: tuple[ExecutionFact, ...]
    confirmations: tuple[Confirmation, ...]
    currency: CurrencyReference
    read_started_at: datetime
    read_completed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionTime:
    time_precision: Literal["TIMESTAMP", "DATE_ONLY", "UNKNOWN"]
    executed_at: datetime | None
    executed_on: date | None
    execution_timezone: str | None
    recorded_at: datetime
    possible_start_at: datetime | None
    possible_end_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSource(ExecutionTime):
    execution_id: UUID
    trade_id: UUID
    product_id: UUID
    side: str
    quantity: int
    price_per_unit: str | None
    recorded_by: UUID
    supersedes_execution_id: UUID | None
    superseded_by_execution_id: UUID | None
    is_effective: bool
    currency_confirmation: Confirmation | None
    currency_history: tuple[Confirmation, ...]
    currency_resolution: ExecutionCurrencyResolution


@dataclass(frozen=True, slots=True, kw_only=True)
class SellItem(ExecutionTime):
    execution_id: UUID
    trade_id: UUID
    product_id: UUID
    product_name: str | None
    origin: str
    quantity: int
    price_per_unit: str | None
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
    open_quantity_before: int | None
    open_quantity_after: int | None
    currency_confirmation_ids: tuple[UUID, ...]
    cost_basis_execution_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ExcludedTrade:
    trade_id: UUID
    product_id: UUID
    product_name: str | None
    origin: str
    reason: Literal["TRADE_CANCELLED"]
    execution_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ReportCounts:
    examined: int
    in_period: int
    outside_period: int
    period_ambiguous: int
    period_unknown: int
    candidates: int
    usable: int
    unresolved: int
    excluded: int
    cancelled: int


@dataclass(frozen=True, slots=True)
class ReportSummary:
    status: SummaryStatus
    total: str | None
    total_display: str | None
    subtotal: str | None
    subtotal_display: str | None
    rounding_difference: str | None
    rounding_difference_display: str | None


@dataclass(frozen=True, slots=True)
class ReportBasis:
    id: str
    read_started_at: datetime
    read_completed_at: datetime
    calculated_at: datetime
    knowledge: Literal["CURRENT_EFFECTIVE_FACTS"] = "CURRENT_EFFECTIVE_FACTS"


@dataclass(frozen=True, slots=True)
class RealizedGrossReport:
    definition_version: str
    filters: ReportFilters
    interval_start_at: datetime
    interval_end_at: datetime
    basis: ReportBasis
    currency: CurrencyReference
    summary: ReportSummary
    counts: ReportCounts
    items: tuple[SellItem, ...]
    sources: tuple[ExecutionSource, ...]
    excluded_trades: tuple[ExcludedTrade, ...]
