"""FastAPI dependencies for the FT-001 REST adapter."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import ApplicationContainer, get_container
from app.database.dependencies import get_database_session
from app.features.analysis.service.reference_application import (
    MarketReferenceAnalysisService,
)
from app.features.market.service.issuer_administration import IssuerAdministrationService
from app.features.market.service.listing_service import ListingService
from app.features.market.service.reference_data_service import ReferenceDataService
from app.features.market.service.service import UnderlyingService
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market.service.top_down_readiness import (
    MarketDataTopDownReferenceAdministrationService,
)
from app.features.market.service.trading_venue_administration import (
    TradingVenueAdministrationService,
)
from app.features.market.service.unit_of_work import SqlAlchemyMarketUnitOfWork
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService


async def get_underlying_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UnderlyingService:
    return UnderlyingService(SqlAlchemyMarketUnitOfWork(session))


async def get_listing_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ListingService:
    return ListingService(SqlAlchemyMarketUnitOfWork(session))


async def get_reference_data_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ReferenceDataService:
    return ReferenceDataService(SqlAlchemyMarketUnitOfWork(session))


async def get_issuer_administration_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IssuerAdministrationService:
    return IssuerAdministrationService(SqlAlchemyMarketUnitOfWork(session))


async def get_trading_venue_administration_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TradingVenueAdministrationService:
    return TradingVenueAdministrationService(SqlAlchemyMarketUnitOfWork(session))


async def get_top_down_reference_administration_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TopDownReferenceAdministrationService:
    return MarketDataTopDownReferenceAdministrationService(session)


async def get_market_reference_analysis_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> MarketReferenceAnalysisService:
    return MarketReferenceAnalysisService(session)


async def get_reference_market_data_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ReferenceMarketDataService:
    runtime = container.eodhd
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EODHD provider is disabled",
        )
    settings = container.settings.market_data.eodhd
    return ReferenceMarketDataService(
        session,
        client=runtime.client,
        call_budget=runtime.call_budget,
        retry_policy=runtime.retry_policy,
        rate_limiter=runtime.rate_limiter,
        provider_call_cost=settings.historical_eod_call_cost,
    )