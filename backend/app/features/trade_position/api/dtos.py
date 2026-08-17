"""REST DTOs for FT-009 purchase execution capture."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.trade_position.domain.enums import TradeOrigin


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
    opened_at: datetime
    last_execution_at: datetime


class InitialPurchaseResponse(BaseModel):
    trade: TradeResponse
    execution: ExecutionResponse
    position: PositionResponse


class AdditionalPurchaseResponse(BaseModel):
    execution: ExecutionResponse
    position: PositionResponse
