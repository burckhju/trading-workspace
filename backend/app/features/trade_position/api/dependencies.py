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


def _allowed_warrant_quote_providers(
    container: ApplicationContainer,
) -> frozenset[MarketDataProvider]:
    allowed: set[MarketDataProvider] = set()
    if (
        container.frankfurt is not None
        and container.settings.market_data.frankfurt.readiness_reason == "CONFIGURED_NOT_PROBED"
    ):
        allowed.add(MarketDataProvider.FRANKFURT_QUOTES)
    if container.vontobel is not None:
        allowed.add(MarketDataProvider.VONTOBEL_MARKETS)
    stuttgart = container.settings.market_data.stuttgart_delayed
    if (
        container.stuttgart is not None
        and stuttgart.has_verified_schema
        and stuttgart.has_source_configuration
    ):
        allowed.add(MarketDataProvider.BOERSE_STUTTGART_DELAYED)
    if container.gettex is not None:
        allowed.add(MarketDataProvider.GETTEX_DELAYED)
    return frozenset(allowed)


def get_trade_position_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> TradePositionService:
    allowed_providers = _allowed_warrant_quote_providers(container)
    return TradePositionService(
        uow=SqlAlchemyTradePositionUnitOfWork(session),
        workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
        products=WarrantProductResolver(WarrantService(session)),
        quote_source_selector=PositionQuoteSourceSelector(
            PositionQuoteSourceSelectionRepository(session),
            allowed_providers,
        ),
    )
