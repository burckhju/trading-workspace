"""Explicit destructive TradePlan hard-delete endpoint."""

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.features.trade_plan.api.dependencies import get_trade_plan_hard_delete_service
from app.features.trade_plan.api.dtos import TradePlanDeletionResponse
from app.features.trade_plan.api.errors import translate_trade_plan_error
from app.features.trade_plan.service.hard_delete import TradePlanHardDeleteService

router = APIRouter(prefix="/api/v1/trade-plans", tags=["trade-plans"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.delete("/{trade_plan_id}", response_model=TradePlanDeletionResponse)
async def hard_delete_trade_plan(
    trade_plan_id: UUID,
    service: Annotated[TradePlanHardDeleteService, Depends(get_trade_plan_hard_delete_service)],
) -> TradePlanDeletionResponse:
    try:
        summary = await service.delete(workspace_id=WORKSPACE_ID, trade_plan_id=trade_plan_id)
        return TradePlanDeletionResponse(**asdict(summary))
    except ValueError as exc:
        raise translate_trade_plan_error(exc) from exc
