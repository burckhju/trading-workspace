"""Request-scoped FT-008 dependencies."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.product_selection.persistence.unit_of_work import (
    SqlAlchemyProductSelectionUnitOfWork,
)
from app.features.product_selection.service.application import ProductSelectionService
from app.features.product_selection.service.commands import ProductSelectionCommandService
from app.features.product_selection.service.persistence import (
    ProductSelectionPersistenceService,
    sqlalchemy_persistence_service,
)
from app.features.product_selection.service.queries import ProductSelectionQueryService


async def get_product_selection_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProductSelectionService]:
    yield ProductSelectionService(session)


async def get_product_selection_persistence_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProductSelectionPersistenceService]:
    yield sqlalchemy_persistence_service(session)


async def get_product_selection_query_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProductSelectionQueryService]:
    yield ProductSelectionQueryService(session)


async def get_product_selection_command_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProductSelectionCommandService]:
    yield ProductSelectionCommandService(SqlAlchemyProductSelectionUnitOfWork(session))
