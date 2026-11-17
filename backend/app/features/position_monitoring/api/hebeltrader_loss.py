"""GET-only B04/B57 status; activation belongs to central deployment configuration."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.core.di import get_application_settings
from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.position_monitoring.service.hebeltrader_loss_read import (
    HebeltraderLossReader,
    LossStatusReport,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_loss_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
    settings: Annotated[Settings, Depends(get_application_settings)],
) -> HebeltraderLossReader:
    monitoring = settings.position_monitoring
    return HebeltraderLossReader(
        database.engine,
        scope=monitoring.hebeltrader_scope,
        runner_enabled=monitoring.enabled,
    )


@router.get("/trades/{trade_id}/hebeltrader-loss")
async def read_loss_status(
    trade_id: UUID,
    position_id: UUID,
    reader: Annotated[HebeltraderLossReader, Depends(get_loss_reader)],
    request: Request,
) -> LossStatusReport:
    if (
        set(request.query_params) != {"position_id"}
        or len(request.query_params.getlist("position_id")) != 1
    ):
        raise ApplicationError(
            code="B04_POSITION_QUERY_INVALID",
            message="Genau eine Position erforderlich.",
            status_code=422,
        )
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except (DBAPIError, ValueError) as error:
        raise ApplicationError(
            code="B04_STATUS_UNAVAILABLE",
            message="Der gespeicherte Regelstand konnte nicht gelesen werden.",
            status_code=503,
        ) from error
