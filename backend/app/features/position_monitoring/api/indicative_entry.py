"""GET-only review status; activation remains a central operating setting."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.core.di import get_application_settings
from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.position_monitoring.service.indicative_entry_read import (
    IndicativeEntryReader,
    IndicativeStatusReport,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_indicative_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
    settings: Annotated[Settings, Depends(get_application_settings)],
) -> IndicativeEntryReader:
    monitoring = settings.position_monitoring
    return IndicativeEntryReader(
        database.engine,
        scope=monitoring.review_scope,
        runner_enabled=monitoring.enabled,
        notifications_enabled=(
            monitoring.review_notifications_enabled and settings.notification.telegram.enabled
        ),
    )


@router.get("/trades/{trade_id}/indicative-entry")
async def read_indicative_status(
    trade_id: UUID,
    position_id: UUID,
    reader: Annotated[IndicativeEntryReader, Depends(get_indicative_reader)],
    request: Request,
) -> IndicativeStatusReport:
    if (
        set(request.query_params) != {"position_id"}
        or len(request.query_params.getlist("position_id")) != 1
    ):
        raise ApplicationError(
            code="REVIEW_POSITION_QUERY_INVALID",
            message="Genau eine Position erforderlich.",
            status_code=422,
        )
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except (DBAPIError, ValueError) as error:
        raise ApplicationError(
            code="REVIEW_STATUS_UNAVAILABLE",
            message="Der gespeicherte Reviewstand konnte nicht gelesen werden.",
            status_code=503,
        ) from error
