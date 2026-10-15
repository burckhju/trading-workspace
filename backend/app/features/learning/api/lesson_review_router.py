"""Thin explicit-review API using the existing FT-012 objects and identity boundary."""

from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.core.identity.context import RequestIdentity, get_request_identity
from app.database.dependencies import get_database_session
from app.features.learning.api.dependencies import UtcClock, UuidFactory
from app.features.learning.api.errors import translate_lesson_error, translate_lesson_review_error
from app.features.learning.application.lesson_review_commands import (
    LessonReviewCommand,
    LessonReviewCommands,
    LessonReviewReceipt,
    ReviewCommandError,
    ReviewOperation,
)
from app.features.learning.application.lesson_review_query import (
    EvidenceSourceInspection,
    LessonReviewContext,
    LessonReviewQuery,
)
from app.features.learning.application.lesson_review_service import LessonReviewServiceError
from app.features.learning.application.lesson_service import LessonEvidenceInput, LessonServiceError
from app.features.learning.domain import LessonEvidenceRelation, LessonState
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)
from app.features.post_trade.api.dependencies import get_exit_review_service

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
WORKSPACE = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR = UUID("00000000-0000-4000-8000-000000000002")


def get_review_commands(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonReviewCommands:
    return LessonReviewCommands(
        uow=cast(LearningTradeLinkUnitOfWork, SqlAlchemyLearningTradeLinkUnitOfWork(session)),
        clock=UtcClock(),
        id_factory=UuidFactory(),
    )


def get_review_query(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonReviewQuery:
    return LessonReviewQuery(
        uow=cast(LearningTradeLinkUnitOfWork, SqlAlchemyLearningTradeLinkUnitOfWork(session)),
        inspector=get_exit_review_service(session),
        clock=UtcClock(),
    )


class ReviewRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_current_version_id: UUID
    expected_current_state: LessonState
    expected_open_signal_id: UUID | None
    reason: str = Field(min_length=1, max_length=200)
    confirmed: Literal[True]


class SourceReviewRequest(ReviewRequestBase):
    operation: Literal["OPEN_SOURCE_REVIEW"]
    reviewed_evidence_ids: list[UUID] = Field(min_length=1)


class ContradictionReviewRequest(ReviewRequestBase):
    operation: Literal["OPEN_CONTRADICTION_REVIEW"]
    contradiction_link_ids: list[UUID] = Field(min_length=1)


class ResolveReviewRequest(ReviewRequestBase):
    operation: Literal["CONFIRM_UNCHANGED", "RETIRE"]


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_evidence_id: UUID
    relation: LessonEvidenceRelation


class NewVersionRequest(ReviewRequestBase):
    operation: Literal["NEW_VERSION"]
    main_category: str = Field(min_length=1)
    content: str = Field(min_length=1)
    evidence: list[EvidenceInput] = Field(min_length=1)


ReviewRequest = Annotated[
    SourceReviewRequest | ContradictionReviewRequest | ResolveReviewRequest | NewVersionRequest,
    Field(discriminator="operation"),
]
Commands = Annotated[LessonReviewCommands, Depends(get_review_commands)]
Query = Annotated[LessonReviewQuery, Depends(get_review_query)]


def _error(error: ReviewCommandError) -> ApplicationError:
    code = 404 if error.code.endswith("NOT_FOUND") else 409
    if error.code == "LESSON_REVIEW_INVALID":
        code = 422
    return ApplicationError(code=error.code, message=str(error), status_code=code)


@router.get("/lessons/{lesson_id}/review-context", response_model=LessonReviewContext)
async def review_context(lesson_id: UUID, query: Query) -> LessonReviewContext:
    try:
        return await query.context(workspace_id=WORKSPACE, lesson_id=lesson_id)
    except ReviewCommandError as error:
        raise _error(error) from error


@router.get("/learning-evidence/{evidence_id}/currentness", response_model=EvidenceSourceInspection)
async def evidence_currentness(evidence_id: UUID, query: Query) -> EvidenceSourceInspection:
    try:
        return await query.source(workspace_id=WORKSPACE, evidence_id=evidence_id)
    except ReviewCommandError as error:
        raise _error(error) from error


@router.post("/lessons/{lesson_id}/review-commands", response_model=LessonReviewReceipt)
async def execute_review(
    lesson_id: UUID,
    request: ReviewRequest,
    commands: Commands,
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> LessonReviewReceipt:
    try:
        actor = LOCAL_ACTOR if identity.actor_id == "local-user" else UUID(identity.actor_id)
    except ValueError as error:
        raise ApplicationError(
            code="INVALID_ACTOR", message="Actor must be a UUID", status_code=422
        ) from error
    values = request.model_dump(exclude={"confirmed", "operation", "evidence"})
    for name in ("reviewed_evidence_ids", "contradiction_link_ids"):
        if name in values:
            values[name] = tuple(values[name])
    evidence = (
        tuple(
            LessonEvidenceInput(item.learning_evidence_id, item.relation)
            for item in request.evidence
        )
        if isinstance(request, NewVersionRequest)
        else ()
    )
    command = LessonReviewCommand(
        operation=ReviewOperation(request.operation), evidence=evidence, **values
    )
    try:
        return await commands.execute(
            workspace_id=WORKSPACE,
            lesson_id=lesson_id,
            actor_id=actor,
            idempotency_key=idempotency_key,
            command=command,
        )
    except ReviewCommandError as error:
        raise _error(error) from error
    except LessonServiceError as error:
        raise translate_lesson_error(error) from error
    except LessonReviewServiceError as error:
        raise translate_lesson_review_error(error) from error
