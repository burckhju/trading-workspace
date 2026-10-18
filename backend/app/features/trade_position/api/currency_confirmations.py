"""Explicit currency provenance commands and side-effect-free history reads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.features.trade_position.api.dependencies import get_execution_currency_confirmation_service
from app.features.trade_position.api.dtos import (
    ExecutionCurrencyConfirmationRequest,
    ExecutionCurrencyConfirmationResponse,
    ExecutionCurrencyHistoryResponse,
)
from app.features.trade_position.service.currency_confirmations import (
    ExecutionCurrencyConfirmationService,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")
PATH = "/trades/{trade_id}/executions/{execution_id}/currency-confirmations"


@router.get(PATH, response_model=ExecutionCurrencyHistoryResponse)
async def currency_history(
    trade_id: UUID,
    execution_id: UUID,
    service: Annotated[
        ExecutionCurrencyConfirmationService, Depends(get_execution_currency_confirmation_service)
    ],
) -> ExecutionCurrencyHistoryResponse:
    current, history = await service.history(WORKSPACE_ID, trade_id, execution_id)
    return ExecutionCurrencyHistoryResponse(
        current=(
            ExecutionCurrencyConfirmationResponse.model_validate(current)
            if current is not None
            else None
        ),
        history=[ExecutionCurrencyConfirmationResponse.model_validate(item) for item in history],
    )


@router.post(PATH, response_model=ExecutionCurrencyConfirmationResponse, status_code=201)
async def confirm_currency(
    trade_id: UUID,
    execution_id: UUID,
    request: ExecutionCurrencyConfirmationRequest,
    service: Annotated[
        ExecutionCurrencyConfirmationService, Depends(get_execution_currency_confirmation_service)
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ExecutionCurrencyConfirmationResponse:
    confirmation = await service.confirm(
        workspace_id=WORKSPACE_ID,
        trade_id=trade_id,
        execution_id=execution_id,
        declaration=request.to_domain(),
        actor=actor_id or LOCAL_ACTOR_ID,
        request_id=request.request_id,
        supersedes_confirmation_id=request.supersedes_confirmation_id,
    )
    return ExecutionCurrencyConfirmationResponse.model_validate(confirmation)
