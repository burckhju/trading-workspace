"""Explicit original HTML import; identities, hashes and revisions stay server-owned."""

import base64
import binascii
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.product.domain.deadline_listing_terms import ProductListingTermsRead
from app.features.product.service.deadline_listing_terms import (
    ProductListingTermsImportService,
    ProductListingTermsReader,
    listing_terms_error,
)
from app.providers.product_listing_terms import MAX_BYTES

router = APIRouter(prefix="/{warrant_id}/deadline-listing-terms")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class OriginalListingTermsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_base64: str = Field(min_length=1, max_length=((MAX_BYTES + 2) // 3) * 4)


class WithdrawListingTermsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision_number: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1000)


def get_listing_terms_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> ProductListingTermsReader:
    return ProductListingTermsReader(database.engine)


def get_listing_terms_importer(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProductListingTermsImportService:
    return ProductListingTermsImportService(session)


def no_query(request: Request) -> None:
    if request.query_params:
        raise listing_terms_error(
            "PRODUCT_LISTING_TERMS_QUERY_INVALID", "Keine Queryparameter erlaubt."
        )


@router.get("/current")
async def current_listing_terms(
    warrant_id: UUID,
    reader: Annotated[ProductListingTermsReader, Depends(get_listing_terms_reader)],
    request: Request,
) -> ProductListingTermsRead:
    no_query(request)
    return await reader.read(workspace_id=WORKSPACE_ID, warrant_id=warrant_id)


@router.post("/imports", status_code=201)
async def import_listing_terms(
    warrant_id: UUID,
    payload: OriginalListingTermsRequest,
    service: Annotated[ProductListingTermsImportService, Depends(get_listing_terms_importer)],
    request: Request,
) -> ProductListingTermsRead:
    no_query(request)
    try:
        document = base64.b64decode(payload.document_base64, validate=True)
    except (ValueError, binascii.Error) as error:
        raise listing_terms_error(
            "PRODUCT_LISTING_TERMS_FILE_INVALID", "Originaldatei ungültig."
        ) from error
    return await service.record(
        workspace_id=WORKSPACE_ID, warrant_id=warrant_id, actor_id=ACTOR_ID, document=document
    )


@router.post("/withdrawals")
async def withdraw_listing_terms(
    warrant_id: UUID,
    payload: WithdrawListingTermsRequest,
    service: Annotated[ProductListingTermsImportService, Depends(get_listing_terms_importer)],
    request: Request,
) -> ProductListingTermsRead:
    no_query(request)
    return await service.withdraw(
        workspace_id=WORKSPACE_ID, warrant_id=warrant_id, actor_id=ACTOR_ID, **payload.model_dump()
    )
