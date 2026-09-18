"""FastAPI dependencies for FT-009 Trade & Position."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import ApplicationContainer, get_container
from app.database.dependencies import get_database_session
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import PositionQuoteSourceSelector
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
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> TradePositionService:
    allowed_providers = {
        provider
        for provider, adapter in (
            (MarketDataProvider.FRANKFURT_QUOTES, container.frankfurt),
            (MarketDataProvider.VONTOBEL_MARKETS, container.vontobel),
            (MarketDataProvider.BOERSE_STUTTGART_DELAYED, container.stuttgart),
            (MarketDataProvider.GETTEX_DELAYED, container.gettex),
        )
        if adapter is not None
    }
    return TradePositionService(
        uow=SqlAlchemyTradePositionUnitOfWork(session),
        workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
        products=WarrantProductResolver(WarrantService(session)),
        quote_source_selector=PositionQuoteSourceSelector(
            PositionQuoteSourceSelectionRepository(session),
            allowed_providers,
        ),
    )
