"""FastAPI dependencies for FT-009 Trade & Position."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.product.service.application import WarrantService
from app.features.trade_position.persistence.unit_of_work import (
    SqlAlchemyTradePositionUnitOfWork,
)
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import (
    SqlAlchemyWorkspaceSelectionResolver,
    WarrantProductResolver,
)


def get_trade_position_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TradePositionService:
    return TradePositionService(
        uow=SqlAlchemyTradePositionUnitOfWork(session),
        workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
        products=WarrantProductResolver(WarrantService(session)),
    )
