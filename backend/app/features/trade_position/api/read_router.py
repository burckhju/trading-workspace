"""Read endpoints for persisted trade provenance."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.trade_position.api.dtos import TradeResponse
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.persistence.repositories import SqlAlchemyTradeRepository
from app.features.trade_position.service.read import TradeReadService

router = APIRouter(
    prefix="/api/v1/trade-position",
    tags=["trade-position"],
)

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_trade_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TradeReadService:
    return TradeReadService(SqlAlchemyTradeRepository(session))


def _response(value: Trade) -> TradeResponse:
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


@router.get("/trades/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: UUID,
    service: Annotated[TradeReadService, Depends(get_trade_read_service)],
) -> TradeResponse:
    try:
        trade = await service.get_trade(workspace_id=WORKSPACE_ID, trade_id=trade_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _response(trade)
