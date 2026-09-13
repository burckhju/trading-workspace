"""Read-before-confirm cancellation API. Never sends a broker order."""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.trade_position.api.router import LOCAL_ACTOR_ID, WORKSPACE_ID
from app.features.trade_position.service.cancellation import TradeCancellationService

router = APIRouter(prefix="/api/v1/trade-position/trades", tags=["trade-position"])


class CancellationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_product_id: UUID
    expected_state_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=1000)
    duplicate_of_trade_id: UUID | None = None
    confirmed: Literal[True]


@router.get("/{trade_id}/cancellation")
async def cancellation_preview(
    trade_id: UUID, session: Annotated[AsyncSession, Depends(get_database_session)]
) -> dict[str, Any]:
    return await TradeCancellationService(session).preview(WORKSPACE_ID, trade_id)


@router.post("/{trade_id}/cancel")
async def cancel_trade(
    trade_id: UUID,
    request: CancellationRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> dict[str, Any]:
    return await TradeCancellationService(session).cancel(
        workspace_id=WORKSPACE_ID,
        trade_id=trade_id,
        expected_product_id=request.expected_product_id,
        expected_state_token=request.expected_state_token,
        reason=request.reason,
        actor=actor_id or LOCAL_ACTOR_ID,
        duplicate_of_trade_id=request.duplicate_of_trade_id,
    )
