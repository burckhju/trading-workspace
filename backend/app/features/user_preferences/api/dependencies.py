from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.user_preferences.service.application import UserPreferenceService


async def get_user_preference_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[UserPreferenceService]:
    yield UserPreferenceService(session)
