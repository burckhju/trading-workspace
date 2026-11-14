"""Read-only target history and an explicitly confirmed assessment command."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import TargetAssessmentRecord
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
    TargetAssessmentCommand,
)
from app.features.position_monitoring.service.hebeltrader_targets import (
    HebeltraderTargetReader,
    HebeltraderTargetService,
    target_error,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class TargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ComparisonQualificationInput(TargetInput):
    history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    listing_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_version_id: UUID
    source_scale_reference: str = Field(min_length=3, max_length=1000)
    evidence_reference: str = Field(min_length=3, max_length=1000)
    confirmation: Literal["CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE"]

    def to_domain(self) -> TargetComparisonQualification:
        return TargetComparisonQualification(
            history_fingerprint=self.history_fingerprint,
            listing_fingerprint=self.listing_fingerprint,
            source_version_id=self.source_version_id,
            source_scale_reference=self.source_scale_reference,
            evidence_reference=self.evidence_reference,
        )


class TargetAssessmentRequest(TargetInput):
    position_id: UUID
    request_id: UUID
    expected_basis_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_assessment_id: UUID | None
    confirmation: Literal["ASSESS_SAVED_HEBELTRADER_EVIDENCE"]
    qualification: ComparisonQualificationInput | None = None

    def to_domain(self) -> TargetAssessmentCommand:
        return TargetAssessmentCommand(
            position_id=self.position_id,
            request_id=self.request_id,
            expected_basis_id=self.expected_basis_id,
            expected_assessment_id=self.expected_assessment_id,
            qualification=self.qualification.to_domain() if self.qualification else None,
        )


def get_target_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> HebeltraderTargetReader:
    return HebeltraderTargetReader(database.engine)


def get_target_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> HebeltraderTargetService:
    return HebeltraderTargetService(session)


Reader = Annotated[HebeltraderTargetReader, Depends(get_target_reader)]


def _position_query(request: Request) -> None:
    if len(request.query_params.getlist("position_id")) != 1:
        raise target_error(
            "HEBELTRADER_POSITION_INVALID",
            "Eine eindeutige Positionskennung ist erforderlich.",
            422,
        )


def _read_unavailable() -> ApplicationError:
    return target_error(
        "HEBELTRADER_TARGET_READ_UNAVAILABLE",
        "Die Zielhistorie konnte nicht gelesen werden. Daraus folgt keine Entwarnung.",
        503,
    )


@router.get("/trades/{trade_id}/hebeltrader-targets")
async def targets(
    trade_id: UUID, position_id: UUID, reader: Reader, request: Request
) -> HebeltraderTargetsReport:
    _position_query(request)
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except DBAPIError as error:
        raise _read_unavailable() from error


@router.get("/trades/{trade_id}/hebeltrader-targets/assessments/{assessment_id}")
async def assessment(
    trade_id: UUID,
    position_id: UUID,
    assessment_id: UUID,
    reader: Reader,
    request: Request,
) -> TargetAssessmentRecord:
    _position_query(request)
    try:
        return await reader.assessment(WORKSPACE_ID, trade_id, position_id, assessment_id)
    except DBAPIError as error:
        raise _read_unavailable() from error


@router.post("/trades/{trade_id}/hebeltrader-targets/assessments")
async def assess(
    trade_id: UUID,
    body: TargetAssessmentRequest,
    service: Annotated[HebeltraderTargetService, Depends(get_target_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> HebeltraderTargetsReport:
    try:
        return await service.assess(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            command=body.to_domain(),
            actor=actor_id or LOCAL_ACTOR_ID,
        )
    except DBAPIError as error:
        raise target_error(
            "HEBELTRADER_TARGET_WRITE_UNCONFIRMED",
            (
                "Der Ausgang der Belegprüfung konnte nicht bestätigt werden. Gespeicherten "
                "Prüfstand lesen."
            ),
            503,
        ) from error
