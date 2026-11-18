"""GET-only stored product-date review state; global activation remains explicit."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.core.di import get_application_settings
from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.position_monitoring.service.product_deadline_review_read import (
    ProductDeadlineReviewReader,
    ProductDeadlineStatusReport,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_product_deadline_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
    settings: Annotated[Settings, Depends(get_application_settings)],
) -> ProductDeadlineReviewReader:
    monitoring = settings.position_monitoring
    return ProductDeadlineReviewReader(
        database.engine,
        scope=monitoring.review_scope,
        runner_enabled=monitoring.enabled,
        notifications_enabled=(
            monitoring.review_scope == "INDICATIVE_ENTRY_V2"
            and monitoring.review_notifications_enabled
            and settings.notification.telegram.enabled
        ),
    )


@router.get("/trades/{trade_id}/product-deadline-review")
async def read_product_deadline_status(
    trade_id: UUID,
    position_id: UUID,
    reader: Annotated[ProductDeadlineReviewReader, Depends(get_product_deadline_reader)],
    request: Request,
) -> ProductDeadlineStatusReport:
    if (
        set(request.query_params) != {"position_id"}
        or len(request.query_params.getlist("position_id")) != 1
    ):
        raise ApplicationError(
            code="PRODUCT_DEADLINE_POSITION_QUERY_INVALID",
            message="Genau eine Position erforderlich.",
            status_code=422,
        )
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except (DBAPIError, ValueError) as error:
        raise ApplicationError(
            code="PRODUCT_DEADLINE_STATUS_UNAVAILABLE",
            message="Der gespeicherte Produktterminstand konnte nicht gelesen werden.",
            status_code=503,
        ) from error
