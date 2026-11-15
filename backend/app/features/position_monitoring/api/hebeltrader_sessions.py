"""Passive session evidence for a single explicitly scoped position."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.position_monitoring.service.hebeltrader_session_contracts import (
    HebeltraderSessionsReport,
)
from app.features.position_monitoring.service.hebeltrader_sessions import HebeltraderSessionReader

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_session_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> HebeltraderSessionReader:
    return HebeltraderSessionReader(database.engine)


@router.get("/trades/{trade_id}/hebeltrader-sessions")
async def read_sessions(
    trade_id: UUID,
    position_id: UUID,
    reader: Annotated[HebeltraderSessionReader, Depends(get_session_reader)],
    request: Request,
) -> HebeltraderSessionsReport:
    if (
        set(request.query_params) != {"position_id"}
        or len(request.query_params.getlist("position_id")) != 1
    ):
        raise ApplicationError(
            code="HEBELTRADER_SESSION_POSITION_INVALID",
            message="Genau eine Positionskennung ist erforderlich; "
            "der Prüfzeitpunkt ist serverseitig.",
            status_code=422,
        )
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except (DBAPIError, ValueError) as error:
        raise ApplicationError(
            code="HEBELTRADER_SESSION_READ_UNAVAILABLE",
            message="Die gespeicherte Sitzungsevidenz konnte nicht gelesen werden. "
            "Dies ist kein Nachweis fehlender Belege oder einer abgeschlossenen Frist.",
            status_code=503,
        ) from error
