"""Request-scoped FT-013 dependencies."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.service.application import ModelGovernanceService


async def get_model_governance_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ModelGovernanceService]:
    yield ModelGovernanceService(session)
