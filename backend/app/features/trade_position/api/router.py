"""REST endpoints for FT-009 Trade & Position."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.features.trade_position.api.dependencies import get_trade_position_service
from app.features.trade_position.api.dtos import (
    AdditionalPurchaseRequest,
    AdditionalPurchaseResponse,
    ExecutionCorrectionRequest,
    ExecutionResponse,
    ExternalPurchaseRequest,
    Ft011EligibilityResponse,
    InitialPurchaseResponse,
    ManagementEventCorrectionRequest,
    PositionResponse,
    PriceManagementRequest,
    SaleRequest,
    TextManagementRequest,
    TradeManagementEventResponse,
    TradeManagementStateResponse,
    TradeResponse,
    TradeTimelineEntryResponse,
    WorkspacePurchaseRequest,
)
from app.features.trade_position.domain.management import TradeManagementState
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
    TradeManagementEvent,
)
from app.features.trade_position.domain.timeline import Ft011Eligibility, TradeTimelineEntry
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
        side=value.side,
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
        realized_gross_pnl=value.realized_gross_pnl,
        opened_at=value.opened_at,
        last_execution_at=value.last_execution_at,
        closed_at=value.closed_at,
        is_closed=value.is_closed,
    )



def _management_event(value: TradeManagementEvent) -> TradeManagementEventResponse:
    return TradeManagementEventResponse(
        id=value.id,
        trade_id=value.trade_id,
        event_type=value.event_type,
        effective_at=value.effective_at,
        recorded_at=value.recorded_at,
        numeric_value=value.numeric_value,
        text_value=value.text_value,
        supersedes_event_id=value.supersedes_event_id,
    )


def _management_state(value: TradeManagementState) -> TradeManagementStateResponse:
    return TradeManagementStateResponse(
        trade_id=value.trade_id,
        stop_price=value.stop_price,
        target_price=value.target_price,
        thesis=value.thesis,
        notes=value.notes,
        last_event_at=value.last_event_at,
    )



def _timeline_entry(value: TradeTimelineEntry) -> TradeTimelineEntryResponse:
    return TradeTimelineEntryResponse(
        id=value.id,
        trade_id=value.trade_id,
        occurred_at=value.occurred_at,
        recorded_at=value.recorded_at,
        kind=value.kind.value,
        execution_side=value.execution_side,
        management_event_type=value.management_event_type,
        quantity=value.quantity,
        price_per_unit=value.price_per_unit,
        numeric_value=value.numeric_value,
        text_value=value.text_value,
        supersedes_id=value.supersedes_id,
    )


def _ft011(value: Ft011Eligibility) -> Ft011EligibilityResponse:
    return Ft011EligibilityResponse(
        trade_id=value.trade_id,
        eligible=value.eligible,
        reason=value.reason,
    )


def _executed_at(value: datetime | None) -> datetime:
    return value or datetime.now(UTC)


def _effective_at(value: datetime | None) -> datetime:
    return value or datetime.now(UTC)


def _translate(error: ValueError) -> HTTPException:
    message = str(error)

    if "not found" in message:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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

@router.post(
    "/trades/{trade_id}/sales",
    response_model=AdditionalPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_sale(
    trade_id: UUID,
    request: SaleRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> AdditionalPurchaseResponse:
    try:
        execution, position = await service.record_sale(
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


@router.post(
    "/trades/{trade_id}/management/stop",
    response_model=TradeManagementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def change_stop(
    trade_id: UUID,
    request: PriceManagementRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeManagementEventResponse:
    try:
        event = await service.change_stop(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            stop_price=request.price,
            effective_at=_effective_at(request.effective_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_event(event)


@router.post(
    "/trades/{trade_id}/management/target",
    response_model=TradeManagementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def change_target(
    trade_id: UUID,
    request: PriceManagementRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeManagementEventResponse:
    try:
        event = await service.change_target(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            target_price=request.price,
            effective_at=_effective_at(request.effective_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_event(event)


@router.post(
    "/trades/{trade_id}/management/thesis",
    response_model=TradeManagementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def update_thesis(
    trade_id: UUID,
    request: TextManagementRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeManagementEventResponse:
    try:
        event = await service.update_thesis(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            thesis=request.text,
            effective_at=_effective_at(request.effective_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_event(event)


@router.post(
    "/trades/{trade_id}/management/notes",
    response_model=TradeManagementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_management_note(
    trade_id: UUID,
    request: TextManagementRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeManagementEventResponse:
    try:
        event = await service.add_management_note(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            note=request.text,
            effective_at=_effective_at(request.effective_at),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_event(event)


@router.get(
    "/trades/{trade_id}/management",
    response_model=TradeManagementStateResponse,
)
async def get_management_state(
    trade_id: UUID,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
) -> TradeManagementStateResponse:
    try:
        state = await service.get_management_state(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_state(state)


@router.get(
    "/trades/{trade_id}/position",
    response_model=PositionResponse,
)
async def get_position(
    trade_id: UUID,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
) -> PositionResponse:
    try:
        position = await service.get_position(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _position(position)

@router.post(
    "/trades/{trade_id}/executions/{execution_id}/corrections",
    response_model=AdditionalPurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def correct_execution(
    trade_id: UUID,
    execution_id: UUID,
    request: ExecutionCorrectionRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> AdditionalPurchaseResponse:
    try:
        execution, position = await service.correct_execution(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            execution_id=execution_id,
            side=request.side,
            quantity=request.quantity,
            price_per_unit=request.price_per_unit,
            executed_at=request.executed_at,
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except ValueError as error:
        raise _translate(error) from error
    return AdditionalPurchaseResponse(
        execution=_execution(execution),
        position=_position(position),
    )


@router.post(
    "/trades/{trade_id}/management/{event_id}/corrections",
    response_model=TradeManagementEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def correct_management_event(
    trade_id: UUID,
    event_id: UUID,
    request: ManagementEventCorrectionRequest,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeManagementEventResponse:
    try:
        event = await service.correct_management_event(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            event_id=event_id,
            effective_at=request.effective_at,
            actor=actor_id or LOCAL_ACTOR_ID,
            numeric_value=request.numeric_value,
            text_value=request.text_value,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _management_event(event)


@router.get(
    "/trades/{trade_id}/timeline",
    response_model=list[TradeTimelineEntryResponse],
)
async def get_trade_timeline(
    trade_id: UUID,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
) -> list[TradeTimelineEntryResponse]:
    try:
        items = await service.get_trade_timeline(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
    except ValueError as error:
        raise _translate(error) from error
    return [_timeline_entry(item) for item in items]


@router.get(
    "/trades/{trade_id}/ft011-eligibility",
    response_model=Ft011EligibilityResponse,
)
async def get_ft011_eligibility(
    trade_id: UUID,
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
) -> Ft011EligibilityResponse:
    try:
        eligibility = await service.get_ft011_eligibility(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
    except ValueError as error:
        raise _translate(error) from error
    return _ft011(eligibility)
