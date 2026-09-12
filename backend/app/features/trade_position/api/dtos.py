"""REST DTOs for FT-009 purchase execution capture."""

from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)


class CaptureTimeRequest(BaseModel):
    executed_at: AwareDatetime | None = None
    executed_on: date | None = None
    execution_timezone: str | None = Field(default=None, max_length=64)
    request_id: UUID | None = None

    @model_validator(mode="after")
    def validate_time(self) -> Self:
        if self.executed_on is not None:
            if self.executed_at is not None or not self.execution_timezone:
                raise ValueError("Supply either an exact timestamp OR a calendar date and timezone")
            try:
                ZoneInfo(self.execution_timezone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ValueError("Unknown execution timezone") from error
        elif self.execution_timezone is not None:
            raise ValueError("A timezone requires a calendar execution date")
        if self.request_id is not None and self.executed_at is None and self.executed_on is None:
            raise ValueError("Idempotent capture requires an explicit execution date or time")
        return self


class WorkspacePurchaseRequest(CaptureTimeRequest):
    product_selection_id: UUID
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)


class ExternalPurchaseRequest(CaptureTimeRequest):
    product_id: UUID
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)


class AdditionalPurchaseRequest(CaptureTimeRequest):
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)


class SaleRequest(CaptureTimeRequest):
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)


class PriceManagementRequest(BaseModel):
    price: Decimal = Field(gt=0)
    effective_at: datetime | None = None


class TextManagementRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    effective_at: datetime | None = None


class ExecutionCorrectionRequest(CaptureTimeRequest):
    side: ExecutionSide
    quantity: int = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def correction_requires_time(self) -> Self:
        if self.executed_at is None and self.executed_on is None:
            raise ValueError("A correction requires an explicit execution date or time")
        if self.request_id is not None:
            raise ValueError(
                "Corrections use the existing supersession identity, not a capture key"
            )
        return self


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
    cancelled_at: datetime | None = None
    cancelled_by: UUID | None = None
    cancellation_reason: str | None = None
    duplicate_of_trade_id: UUID | None = None


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
    executed_on: date | None = None
    execution_timezone: str | None = None


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
    is_cancelled: bool = False
    opened_on: date | None = None
    last_execution_on: date | None = None
    closed_on: date | None = None


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
    executed_on: date | None = None
    execution_timezone: str | None = None


class Ft011EligibilityResponse(BaseModel):
    trade_id: UUID
    eligible: bool
    reason: str
