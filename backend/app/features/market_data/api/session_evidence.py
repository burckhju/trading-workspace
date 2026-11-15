"""Explicit bounded evidence import; GETs are database-enforced read-only snapshots."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.market_data.domain.session_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    InstrumentKind,
    SessionEvidenceCurrent,
    SessionEvidenceImportCommand,
    SessionEvidenceRead,
    SessionEvidenceRevision,
)
from app.features.market_data.persistence.session_evidence import (
    SqlAlchemySessionEvidenceRepository,
)
from app.features.market_data.service.session_evidence import (
    SessionEvidenceImportService,
    SessionEvidenceReader,
    require_instrument,
    session_error,
)

router = APIRouter(prefix="/session-evidence")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class SessionEvidenceRequest(BaseModel):
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
    confirmation: Literal["CONFIRM_OFFICIAL_SESSION_DOCUMENT_REVIEW"]

    def command(self) -> SessionEvidenceImportCommand:
        return SessionEvidenceImportCommand(**self.model_dump(exclude={"confirmation"}))


def get_import_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SessionEvidenceImportService:
    return SessionEvidenceImportService(session)


def get_read_engine(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> AsyncEngine:
    return database.engine


Engine = Annotated[AsyncEngine, Depends(get_read_engine)]
Importer = Annotated[SessionEvidenceImportService, Depends(get_import_service)]


def _single_query(request: Request) -> None:
    for key in request.query_params:
        if len(request.query_params.getlist(key)) != 1:
            raise session_error("SESSION_EVIDENCE_INVALID", "Mehrdeutige Sitzungsabfrage.")


@asynccontextmanager
async def read_snapshot(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False, autoflush=False) as session:
        try:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            yield session
        except (DBAPIError, ValueError) as error:
            raise session_error(
                "SESSION_EVIDENCE_READ_UNAVAILABLE",
                "Sitzungsbelege konnten nicht sicher gelesen werden; dies ist keine Beleglücke.",
                503,
            ) from error
        finally:
            await session.rollback()


@router.post("/imports", status_code=201)
async def import_session_evidence(
    payload: SessionEvidenceRequest,
    service: Importer,
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> SessionEvidenceRevision:
    return await service.record(
        workspace_id=WORKSPACE_ID, actor_id=actor_id or LOCAL_ACTOR_ID, command=payload.command()
    )


@router.get("")
async def read_session_evidence(
    instrument_kind: InstrumentKind,
    instrument_id: UUID,
    start_date: date,
    end_date: date,
    known_at: AwareDatetime,
    engine: Engine,
    request: Request,
    expected_listing_id: UUID | None = None,
) -> SessionEvidenceRead:
    _single_query(request)
    async with read_snapshot(engine) as session:
        return await SessionEvidenceReader(session).read(
            workspace_id=WORKSPACE_ID,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
            known_at=known_at,
            expected_listing_id=expected_listing_id,
        )


@router.get("/current")
async def current_session_evidence(
    instrument_kind: InstrumentKind,
    instrument_id: UUID,
    known_at: AwareDatetime,
    engine: Engine,
    request: Request,
    expected_listing_id: UUID | None = None,
) -> SessionEvidenceCurrent:
    _single_query(request)
    async with read_snapshot(engine) as session:
        return await SessionEvidenceReader(session).current(
            workspace_id=WORKSPACE_ID,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            known_at=known_at,
            expected_listing_id=expected_listing_id,
        )


@router.get("/revisions/{revision_id}")
async def original_session_evidence(
    revision_id: UUID,
    instrument_kind: InstrumentKind,
    instrument_id: UUID,
    engine: Engine,
    request: Request,
) -> SessionEvidenceRevision:
    _single_query(request)
    async with read_snapshot(engine) as session:
        await require_instrument(
            session,
            workspace_id=WORKSPACE_ID,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
        )
        revision = await SqlAlchemySessionEvidenceRepository(session).get(WORKSPACE_ID, revision_id)
        if revision is None or (revision.instrument_kind, revision.instrument_id) != (
            instrument_kind,
            instrument_id,
        ):
            raise session_error(
                "SESSION_EVIDENCE_SCOPE_NOT_FOUND", "Sitzungsrevision nicht gefunden.", 404
            )
        return revision
