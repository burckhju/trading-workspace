"""Strict journal command API; receipts are not mutable draft snapshots."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import ApplicationError
from app.core.identity.context import RequestIdentity, get_request_identity
from app.features.learning.api.journal_dependencies import get_journal_service
from app.features.learning.application.journal_service import (
    JournalCommand,
    JournalError,
    JournalHistory,
    JournalOperation,
    JournalReceipt,
    JournalService,
)

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateDraftRequest(StrictRequest):
    operation: Literal["CREATE_DRAFT"]
    expected_latest_version_id: UUID | None
    expected_exit_review_version_id: UUID
    confirmed: Literal[True]


class SaveDraftRequest(StrictRequest):
    operation: Literal["SAVE_DRAFT"]
    version_id: UUID
    expected_edit_revision: int = Field(ge=1)
    what_went_well: str | None
    would_do_differently: str | None
    additional_notes: str | None


class SourceCommandRequest(StrictRequest):
    operation: Literal["FINALIZE", "REBIND_SOURCE"]
    version_id: UUID
    expected_edit_revision: int = Field(ge=1)
    expected_exit_review_version_id: UUID
    confirmed: Literal[True]


class MaterializeJournalRequest(StrictRequest):
    operation: Literal["MATERIALIZE"]
    version_id: UUID
    confirmed: Literal[True]


JournalRequest = Annotated[
    CreateDraftRequest | SaveDraftRequest | SourceCommandRequest | MaterializeJournalRequest,
    Field(discriminator="operation"),
]
Service = Annotated[JournalService, Depends(get_journal_service)]


def _error(error: JournalError) -> ApplicationError:
    status_code = 404 if error.code == "JOURNAL_NOT_FOUND" else 409
    if error.code == "JOURNAL_INVALID_REQUEST":
        status_code = 422
    return ApplicationError(code=error.code, message=str(error), status_code=status_code)


@router.get("/trades/{trade_id}/journal", response_model=JournalHistory)
async def get_journal(trade_id: UUID, service: Service) -> JournalHistory:
    return await service.history(workspace_id=WORKSPACE_ID, trade_id=trade_id)


@router.get("/journal-versions/{version_id}", response_model=JournalHistory)
async def get_journal_version(version_id: UUID, service: Service) -> JournalHistory:
    try:
        return await service.version(workspace_id=WORKSPACE_ID, version_id=version_id)
    except JournalError as error:
        raise _error(error) from error


@router.post("/trades/{trade_id}/journal/commands", response_model=JournalReceipt)
async def execute_journal_command(
    trade_id: UUID,
    request: JournalRequest,
    service: Service,
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> JournalReceipt:
    try:
        actor_id = LOCAL_ACTOR_ID if identity.actor_id == "local-user" else UUID(identity.actor_id)
    except ValueError as error:
        raise ApplicationError(
            code="INVALID_ACTOR", message="Actor must be a UUID", status_code=422
        ) from error
    values = request.model_dump(exclude={"confirmed", "operation"})
    command = JournalCommand(operation=JournalOperation(request.operation), **values)
    try:
        return await service.execute(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            command=command,
        )
    except JournalError as error:
        raise _error(error) from error
