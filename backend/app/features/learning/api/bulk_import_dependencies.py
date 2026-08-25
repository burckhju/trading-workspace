"""Request-scoped dependency for bulk external-observation imports."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.application.bulk_import_service import (
    ExternalObservationBulkImportService,
)


def get_bulk_import_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ExternalObservationBulkImportService:
    return ExternalObservationBulkImportService(session)
