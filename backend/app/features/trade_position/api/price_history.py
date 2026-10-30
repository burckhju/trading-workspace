"""Position chart GET: existing observations only, no quote resolution or refresh."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.market_data.service.quote_history import QuoteHistoryReader
from app.features.trade_position.api.dependencies import get_trade_position_service
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.price_history import (
    PositionPriceHistory,
    compose_price_history,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.get("/trades/{trade_id}/price-history", response_model=PositionPriceHistory)
async def position_price_history(
    trade_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    service: Annotated[TradePositionService, Depends(get_trade_position_service)],
    days: Annotated[int | None, Query(ge=1, le=366)] = None,
) -> PositionPriceHistory:
    # One short owner/evidence snapshot: concurrent corrections or confirmations
    # cannot change the provenance halfway through composing this response.
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
    try:
        position, executions = await service.get_price_history_context(
            workspace_id=WORKSPACE_ID, trade_id=trade_id
        )
    except ValueError as exc:
        if str(exc) in {"trade not found", "position not found"}:
            raise HTTPException(404, "Position does not exist") from exc
        raise HTTPException(409, "Position history identity could not be verified") from exc
    history = await QuoteHistoryReader(session).prices(
        WORKSPACE_ID, position.product_id, now=datetime.now(UTC), days=days
    )
    if history is None:
        raise HTTPException(404, "Position product does not exist")
    return compose_price_history(position, executions, history)
