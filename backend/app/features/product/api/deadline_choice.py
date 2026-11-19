"""One business selection from saved listings; no manual technical identifiers."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.product.domain.deadline_choice import ProductDeadlineChoiceReport
from app.features.product.service.deadline_choice import (
    ProductDeadlineChoiceReader,
    ProductDeadlineChoiceService,
    choice_error,
)

router = APIRouter(prefix="/{warrant_id}/deadline-exit-listing")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class ProductDeadlineChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: UUID | None
    expected_revision_number: int = Field(ge=0)
    expected_terms_id: UUID
    expected_listing_version: int | None = Field(ge=1)
    expected_venue_version: int | None = Field(ge=1)


def get_deadline_choice_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> ProductDeadlineChoiceReader:
    return ProductDeadlineChoiceReader(database.engine)


def get_deadline_choice_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProductDeadlineChoiceService:
    return ProductDeadlineChoiceService(session)


def no_query(request: Request) -> None:
    if request.query_params:
        raise choice_error(
            "PRODUCT_EXIT_CHOICE_QUERY_INVALID",
            "Diese Produktauswahl erlaubt keine Queryparameter.",
        )


@router.get("")
async def read_deadline_exit_listing(
    warrant_id: UUID,
    reader: Annotated[ProductDeadlineChoiceReader, Depends(get_deadline_choice_reader)],
    request: Request,
) -> ProductDeadlineChoiceReport:
    no_query(request)
    return await reader.read(workspace_id=WORKSPACE_ID, warrant_id=warrant_id)


@router.put("")
async def choose_deadline_exit_listing(
    warrant_id: UUID,
    payload: ProductDeadlineChoiceRequest,
    service: Annotated[ProductDeadlineChoiceService, Depends(get_deadline_choice_service)],
    request: Request,
) -> ProductDeadlineChoiceReport:
    no_query(request)
    return await service.choose(
        workspace_id=WORKSPACE_ID,
        warrant_id=warrant_id,
        actor_id=ACTOR_ID,
        **payload.model_dump(),
    )
