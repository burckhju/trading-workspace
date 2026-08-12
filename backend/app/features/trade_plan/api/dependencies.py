"""Request-scoped FT-007 service dependencies."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.trade_plan.service.application import TradePlanService
from app.features.trade_plan.service.queries import TradePlanQueryService


async def get_trade_plan_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[TradePlanService]:
    yield TradePlanService(session)


async def get_trade_plan_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[TradePlanQueryService]:
    yield TradePlanQueryService(session)
