"""Position-scoped GET only; no quote fetch or rule/execution mutation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.position_monitoring.service.hebeltrader_original_bid import (
    HebeltraderOriginalBidReader,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    HebeltraderOriginalBidReport,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_original_bid_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> HebeltraderOriginalBidReader:
    return HebeltraderOriginalBidReader(database.engine)


@router.get("/trades/{trade_id}/hebeltrader-original-bid")
async def read_original_bid(
    trade_id: UUID,
    position_id: UUID,
    reader: Annotated[HebeltraderOriginalBidReader, Depends(get_original_bid_reader)],
    request: Request,
) -> HebeltraderOriginalBidReport:
    if (
        set(request.query_params) != {"position_id"}
        or len(request.query_params.getlist("position_id")) != 1
    ):
        raise ApplicationError(
            code="HEBELTRADER_ORIGINAL_BID_POSITION_INVALID",
            message="Genau eine Positionskennung ist erforderlich; der Lesestand ist serverseitig.",
            status_code=422,
        )
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except (DBAPIError, ValueError) as error:
        raise ApplicationError(
            code="HEBELTRADER_ORIGINAL_BID_READ_UNAVAILABLE",
            message="Die gespeicherten Geldkursbelege konnten nicht gelesen werden. "
            "Dies ist kein Nachweis fehlender Belege oder einer erfüllten Regel.",
            status_code=503,
        ) from error
