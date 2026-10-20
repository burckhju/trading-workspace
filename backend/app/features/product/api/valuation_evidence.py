"""Explicit user attestation; document URLs are stored, never fetched."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.product.api.errors import translate_product_error
from app.features.product.service.valuation_evidence import (
    ValuationEvidenceService,
    ValuationEvidenceView,
    ValuationFacts,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terms_id: UUID
    expected_version: int = Field(ge=1, strict=True)
    expected_revision: int = Field(ge=0, strict=True)
    facts: ValuationFacts
    confirmation: Literal["CONFIRM_DOCUMENT_REVIEW"]


@router.get("/{warrant_id}/valuation-evidence", response_model=ValuationEvidenceView)
async def read_evidence(
    warrant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ValuationEvidenceView:
    try:
        return await ValuationEvidenceService(session).view(
            WORKSPACE_ID, warrant_id, datetime.now(UTC)
        )
    except Exception as error:
        raise translate_product_error(error) from error


@router.post(
    "/{warrant_id}/valuation-evidence", response_model=ValuationEvidenceView, status_code=201
)
async def record_evidence(
    warrant_id: UUID,
    payload: EvidenceRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ValuationEvidenceView:
    try:
        return await ValuationEvidenceService(session).record(
            workspace_id=WORKSPACE_ID,
            warrant_id=warrant_id,
            actor_id=actor_id or LOCAL_ACTOR_ID,
            now=datetime.now(UTC),
            **payload.model_dump(exclude={"confirmation", "facts"}),
            facts=payload.facts,
        )
    except Exception as error:
        raise translate_product_error(error) from error
