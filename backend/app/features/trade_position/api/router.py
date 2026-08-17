"""REST endpoints for FT-009 Trade & Position."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.features.trade_position.api.dependencies import get_trade_position_service
from app.features.trade_position.api.dtos import (
    AdditionalPurchaseRequest,
    AdditionalPurchaseResponse,
    ExecutionResponse,
    ExternalPurchaseRequest,
    InitialPurchaseResponse,
    PositionResponse,
    TradeResponse,
    WorkspacePurchaseRequest,
)
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.service.application import TradePositionService

router = APIRouter(
    prefix="/api/v1/trade-position",
    tags=["trade-position"],
)

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _trade(value: Trade) -> TradeResponse:
    return TradeResponse(
        id=value.id,
        product_id=value.product_id,
        origin=value.origin,
        trade_plan_id=value.trade_plan_id,
        trade_plan_version_id=value.trade_plan_version_id,
        product_selection_id=value.product_selection_id,
        product_evaluation_id=value.product_evaluation_id,
        created_at=value.created_at,
    )


def _execution(value: ExecutionRecord) -> ExecutionResponse:
    return ExecutionResponse(
        id=value.id,
        trade_id=value.trade_id,
        product_id=value.product_id,
        quantity=value.quantity,
        price_per_unit=value.price_per_unit,
        gross_amount=value.gross_amount,
        executed_at=value.executed_at,
        recorded_at=value.recorded_at,
    )


def _position(value: Position) -> PositionResponse:
    return PositionResponse(
        id=value.id,
        trade_id=value.trade_id,
        product_id=value.product_id,
        open_quantity=value.open_quantity,
        cost_basis=value.cost_basis,
        average_entry_price=value.average_entry_price,
        opened_at=value.opened_at,
        last_execution_at=value.last_execution_at,
    )


def _executed_at(value: datetime | None) -> datetime:
    return value or datetime.now(UTC)


def _translate(error: ValueError) -> HTTPException:
    message = str(error)

    if "not found" in message:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=message,
    )


@router.post(
    "/purchases/from-selection",
    response_model=InitialPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_purchase_from_selection(
    request: WorkspacePurchaseRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> InitialPurchaseResponse:
    try:
        trade, execution, position = await service.record_initial_purchase(
            workspace_id=WORKSPACE_ID,
            product_selection_id=request.product_selection_id,
            quantity=request.quantity,
            price_per_unit=request.price_per_unit,
            executed_at=_executed_at(request.executed_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error

    return InitialPurchaseResponse(
        trade=_trade(trade),
        execution=_execution(execution),
        position=_position(position),
    )


@router.post(
    "/purchases/external",
    response_model=InitialPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_external_purchase(
    request: ExternalPurchaseRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> InitialPurchaseResponse:
    try:
        trade, execution, position = await service.record_external_purchase(
            workspace_id=WORKSPACE_ID,
            product_id=request.product_id,
            quantity=request.quantity,
            price_per_unit=request.price_per_unit,
            executed_at=_executed_at(request.executed_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error

    return InitialPurchaseResponse(
        trade=_trade(trade),
        execution=_execution(execution),
        position=_position(position),
    )


@router.post(
    "/trades/{trade_id}/purchases",
    response_model=AdditionalPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_additional_purchase(
    trade_id: UUID,
    request: AdditionalPurchaseRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> AdditionalPurchaseResponse:
    try:
        execution, position = await service.record_additional_purchase(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            quantity=request.quantity,
            price_per_unit=request.price_per_unit,
            executed_at=_executed_at(request.executed_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error

    return AdditionalPurchaseResponse(
        execution=_execution(execution),
        position=_position(position),
    )
