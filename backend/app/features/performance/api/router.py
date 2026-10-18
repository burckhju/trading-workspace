"""GET never invokes execution, learning, quote or monitoring command services."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.performance.api.dtos import RealizedGrossReportResponse
from app.features.performance.domain.models import ReportFilters
from app.features.performance.domain.report import ReportLimitExceeded
from app.features.performance.service.application import RealizedGrossReportService
from app.features.performance.service.reader import RealizedGrossSnapshotReader

router = APIRouter(prefix="/api/v1/performance", tags=["performance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_realized_gross_service(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> RealizedGrossReportService:
    return RealizedGrossReportService(RealizedGrossSnapshotReader(database.engine))


@router.get("/realized-gross", response_model=RealizedGrossReportResponse)
async def realized_gross_report(
    from_date: date,
    to_date: date,
    report_currency: Annotated[str, Query(pattern=r"^[A-Z]{3}$")],
    report_timezone: Annotated[str, Query(min_length=1, max_length=64)],
    service: Annotated[RealizedGrossReportService, Depends(get_realized_gross_service)],
) -> RealizedGrossReportResponse:
    try:
        return await service.report(
            WORKSPACE_ID, ReportFilters(from_date, to_date, report_currency, report_timezone)
        )
    except ReportLimitExceeded as error:
        raise ApplicationError(
            code="REPORT_RESOURCE_LIMIT",
            status_code=413,
            message=(
                "Die vollständige Auswertung überschreitet die technische Grenze. "
                "Es wurde keine Teilsumme als Gesamtsumme ausgegeben."
            ),
        ) from error
    except ValueError as error:
        raise ApplicationError(
            code="REPORT_INPUT_INVALID",
            status_code=422,
            message="Zeitraum, Berichtszeitzone und Währung prüfen: " + str(error),
        ) from error
    except DBAPIError as error:
        raise ApplicationError(
            code="REPORT_READ_UNAVAILABLE",
            status_code=503,
            message=(
                "Der vollständige Quellenstand konnte nicht gelesen werden. Bitte erneut laden."
            ),
        ) from error
