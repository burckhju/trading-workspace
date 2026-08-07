"""Request-scoped analysis service dependency."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.analysis.service.application import MarketAnalysisService


async def get_market_analysis_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[MarketAnalysisService]:
    yield MarketAnalysisService(session)
