"""Explicit document import and server-clock-only, database-enforced passive reads."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.product.domain.price_scale_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    ProductPriceScaleCurrent,
    ProductPriceScaleImportCommand,
    ProductPriceScaleRevision,
)
from app.features.product.service.price_scale_evidence import (
    ProductPriceScaleEvidenceImportService,
    ProductPriceScaleEvidenceReadService,
    price_scale_error,
)

router = APIRouter(prefix="/{warrant_id}/price-scale-evidence")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class ProductPriceScaleEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    supersedes_revision_id: UUID | None = None
    manifest_json: str = Field(min_length=1, max_length=MAX_MANIFEST_BYTES)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_filename: str = Field(min_length=3, max_length=255)
    document_media_type: str = Field(min_length=1, max_length=100)
    document_base64: str = Field(min_length=1, max_length=((MAX_DOCUMENT_BYTES + 2) // 3) * 4)
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_at: AwareDatetime
    review_reference: str = Field(min_length=3, max_length=1000)
    retrieved_at: AwareDatetime | None = None
    confirmation: Literal["CONFIRM_PRODUCT_PRICE_SCALE_DOCUMENT_REVIEW"]

    @field_validator("reviewed_at", "retrieved_at", mode="before")
    @classmethod
    def explicit_clock(cls, value: object) -> object:
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Original clocks require explicit ISO text with an offset")
        return value

    def command(self) -> ProductPriceScaleImportCommand:
        return ProductPriceScaleImportCommand(**self.model_dump(exclude={"confirmation"}))


def get_import_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProductPriceScaleEvidenceImportService:
    return ProductPriceScaleEvidenceImportService(session)


def get_read_service(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> ProductPriceScaleEvidenceReadService:
    return ProductPriceScaleEvidenceReadService(database.engine)


Reader = Annotated[ProductPriceScaleEvidenceReadService, Depends(get_read_service)]
Importer = Annotated[ProductPriceScaleEvidenceImportService, Depends(get_import_service)]


def no_query(request: Request) -> None:
    if request.query_params:
        raise price_scale_error(
            "PRODUCT_PRICE_SCALE_INVALID",
            "Dieser Produktbeleg-Vertrag erlaubt keine Queryparameter.",
        )


@router.post("/imports", status_code=201)
async def import_price_scale_evidence(
    warrant_id: UUID,
    payload: ProductPriceScaleEvidenceRequest,
    service: Importer,
    request: Request,
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ProductPriceScaleRevision:
    no_query(request)
    return await service.record(
        workspace_id=WORKSPACE_ID,
        warrant_id=warrant_id,
        actor_id=actor_id or LOCAL_ACTOR_ID,
        command=payload.command(),
    )


@router.get("/current")
async def current_price_scale_evidence(
    warrant_id: UUID,
    service: Reader,
    request: Request,
) -> ProductPriceScaleCurrent:
    no_query(request)
    return await service.current(workspace_id=WORKSPACE_ID, warrant_id=warrant_id)


@router.get("/revisions/{revision_id}")
async def original_price_scale_evidence(
    warrant_id: UUID,
    revision_id: UUID,
    service: Reader,
    request: Request,
) -> ProductPriceScaleRevision:
    no_query(request)
    return await service.revision(
        workspace_id=WORKSPACE_ID, warrant_id=warrant_id, revision_id=revision_id
    )
