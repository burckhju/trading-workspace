"""Pure, separately bounded source reads; no editor/command dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.trade_plan.service.queries import TradePlanVersionView
from app.features.trade_position.service.source_view import (
    EvidenceSource,
    JournalSources,
    ReviewSources,
    SourceSnapshot,
    TradeSourceCore,
    TradeSourceReader,
)

router = APIRouter(prefix="/api/v1/trade-position/trades", tags=["trade-position"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_source_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> TradeSourceReader:
    return TradeSourceReader(database.engine)


Reader = Annotated[TradeSourceReader, Depends(get_source_reader)]


def unavailable() -> ApplicationError:
    return ApplicationError(
        code="SOURCE_READ_UNAVAILABLE",
        status_code=503,
        message="Quelle konnte nicht gelesen werden. Das bedeutet nicht, dass sie fehlt.",
    )


def validate_pin(request: Request) -> None:
    if len(request.query_params.getlist("version_id")) > 1:
        raise ApplicationError(
            code="SOURCE_VERSION_INVALID",
            status_code=422,
            message="Mehrdeutiger Versionsbezug. Keine Ersatzversion gewählt.",
        )


@router.get("/{trade_id}/sources")
async def core(trade_id: UUID, reader: Reader) -> SourceSnapshot[TradeSourceCore]:
    try:
        return await reader.core(WORKSPACE_ID, trade_id)
    except DBAPIError as error:
        raise unavailable() from error


@router.get("/{trade_id}/sources/plan")
async def plan(trade_id: UUID, reader: Reader) -> SourceSnapshot[TradePlanVersionView | None]:
    try:
        return await reader.plan(WORKSPACE_ID, trade_id)
    except DBAPIError as error:
        raise unavailable() from error


@router.get("/{trade_id}/sources/reviews")
async def reviews(
    trade_id: UUID, reader: Reader, request: Request, version_id: UUID | None = None
) -> SourceSnapshot[ReviewSources]:
    validate_pin(request)
    try:
        return await reader.reviews(WORKSPACE_ID, trade_id, version_id)
    except DBAPIError as error:
        raise unavailable() from error


@router.get("/{trade_id}/sources/journal")
async def journal(
    trade_id: UUID, reader: Reader, request: Request, version_id: UUID | None = None
) -> SourceSnapshot[JournalSources]:
    validate_pin(request)
    try:
        return await reader.journal(WORKSPACE_ID, trade_id, version_id)
    except DBAPIError as error:
        raise unavailable() from error


@router.get("/{trade_id}/sources/evidence")
async def evidence(trade_id: UUID, reader: Reader) -> SourceSnapshot[tuple[EvidenceSource, ...]]:
    try:
        return await reader.evidence(WORKSPACE_ID, trade_id)
    except DBAPIError as error:
        raise unavailable() from error
