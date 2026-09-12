"""REST contracts for the operational workspace read model."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OperationalActionResponse(BaseModel):
    id: str
    source_feature: str
    action_type: str
    priority: str
    state: str
    title: str
    detail: str
    resource_type: str
    resource_id: UUID
    next_action: str
    target: str
    occurred_at: datetime | None


class OperationalWorkspaceResponse(BaseModel):
    generated_at: datetime
    actions: list[OperationalActionResponse]


class OperationalPositionResponse(BaseModel):
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

    opened_on: date | None = None
    analysis_warning: str | None = None
    quote_source: str | None = None
    quote_observed_at: datetime | None = None


class OperationalPositionsResponse(BaseModel):
    generated_at: datetime
    positions: list[OperationalPositionResponse]
