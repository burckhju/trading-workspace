from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.alert.persistence.read_repository import SqlAlchemyAlertReadRepository


def get_alert_read_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SqlAlchemyAlertReadRepository:
    return SqlAlchemyAlertReadRepository(session)
