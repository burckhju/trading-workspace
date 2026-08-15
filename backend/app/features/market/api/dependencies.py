"""FastAPI dependencies for the FT-001 REST adapter."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.market.service.issuer_administration import IssuerAdministrationService
from app.features.market.service.listing_service import ListingService
from app.features.market.service.reference_data_service import ReferenceDataService
from app.features.market.service.service import UnderlyingService
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market.service.trading_venue_administration import (
    TradingVenueAdministrationService,
)
from app.features.market.service.unit_of_work import SqlAlchemyMarketUnitOfWork


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
    return TopDownReferenceAdministrationService(session)
