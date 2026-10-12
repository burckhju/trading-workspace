"""Stored samples only; a GET does not start a measurement or contact a provider."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.market_data.service.quote_history import QuoteHistoryReader, QuoteHistoryReport

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.get("/warrants/{warrant_id}/quote-history", response_model=QuoteHistoryReport)
async def quote_history(
    warrant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    days: Annotated[int, Query(ge=1, le=31)] = 7,
) -> QuoteHistoryReport:
    result = await QuoteHistoryReader(session).report(
        WORKSPACE_ID, warrant_id, now=datetime.now(UTC), days=days
    )
    if result is None:
        raise HTTPException(404, "Warrant does not exist")
    return result
