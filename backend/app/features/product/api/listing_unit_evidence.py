"""Passive current-unit diagnostics; original import remains a bounded local CLI."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.database.dependencies import get_database_manager
from app.database.manager import DatabaseManager
from app.features.product.domain.listing_unit_evidence import ListingUnitRead
from app.features.product.service.listing_unit_evidence import listing_unit_error
from app.features.product.service.listing_unit_read import ListingUnitEvidenceReadService

router = APIRouter(prefix="/{warrant_id}/listings/{listing_id}/current-unit-evidence")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_read_service(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> ListingUnitEvidenceReadService:
    return ListingUnitEvidenceReadService(database.engine)


@router.get("")
async def current_listing_unit(
    warrant_id: UUID,
    listing_id: UUID,
    request: Request,
    reader: Annotated[ListingUnitEvidenceReadService, Depends(get_read_service)],
) -> ListingUnitRead:
    if request.query_params:
        raise listing_unit_error("LISTING_UNIT_QUERY_INVALID")
    return await reader.read(
        workspace_id=WORKSPACE_ID, warrant_id=warrant_id, listing_id=listing_id
    )
