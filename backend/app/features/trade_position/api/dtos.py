"""REST DTOs for FT-009 purchase execution capture."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)


class WorkspacePurchaseRequest(BaseModel):
    product_selection_id: UUID
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    executed_at: datetime | None = None


class ExternalPurchaseRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    executed_at: datetime | None = None


class AdditionalPurchaseRequest(BaseModel):
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    executed_at: datetime | None = None


class SaleRequest(BaseModel):
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    executed_at: datetime | None = None


class PriceManagementRequest(BaseModel):
    price: Decimal = Field(gt=0)
    effective_at: datetime | None = None


class TextManagementRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    effective_at: datetime | None = None


class ExecutionCorrectionRequest(BaseModel):
    side: ExecutionSide
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    executed_at: datetime


class ManagementEventCorrectionRequest(BaseModel):
    effective_at: datetime
    numeric_value: Decimal | None = Field(default=None, gt=0)
    text_value: str | None = Field(default=None, min_length=1, max_length=4000)


class TradeResponse(BaseModel):
    id: UUID
    product_id: UUID
    origin: TradeOrigin
    trade_plan_id: UUID | None
    trade_plan_version_id: UUID | None
    product_selection_id: UUID | None
    product_evaluation_id: UUID | None
    created_at: datetime


class ExecutionResponse(BaseModel):
    id: UUID
    trade_id: UUID
    product_id: UUID
    side: ExecutionSide
    quantity: int
    price_per_unit: Decimal
    gross_amount: Decimal
    executed_at: datetime
    recorded_at: datetime


class PositionResponse(BaseModel):
    id: UUID
    trade_id: UUID
    product_id: UUID
    open_quantity: int
    cost_basis: Decimal
    average_entry_price: Decimal
    realized_gross_pnl: Decimal
    opened_at: datetime
    last_execution_at: datetime
    closed_at: datetime | None
    is_closed: bool


class InitialPurchaseResponse(BaseModel):
    trade: TradeResponse
    execution: ExecutionResponse
    position: PositionResponse


class AdditionalPurchaseResponse(BaseModel):
    execution: ExecutionResponse
    position: PositionResponse


class TradeManagementEventResponse(BaseModel):
    id: UUID
    trade_id: UUID
    event_type: TradeManagementEventType
    effective_at: datetime
    recorded_at: datetime
    numeric_value: Decimal | None
    text_value: str | None
    supersedes_event_id: UUID | None


class TradeManagementStateResponse(BaseModel):
    trade_id: UUID
    stop_price: Decimal | None
    target_price: Decimal | None
    thesis: str | None
    notes: tuple[str, ...]
    last_event_at: datetime | None


class TradeTimelineEntryResponse(BaseModel):
    id: UUID
    trade_id: UUID
    occurred_at: datetime
    recorded_at: datetime
    kind: str
    execution_side: ExecutionSide | None
    management_event_type: TradeManagementEventType | None
    quantity: int | None
    price_per_unit: Decimal | None
    numeric_value: Decimal | None
    text_value: str | None
    supersedes_id: UUID | None


class Ft011EligibilityResponse(BaseModel):
    trade_id: UUID
    eligible: bool
    reason: str
