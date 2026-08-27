from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.ft011_materialization_service import (
    COMMAND_TYPE,
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
    MaterializeFt011LearningEvidenceService,
    request_fingerprint,
)
from app.features.learning.domain import (
    FT011Evidence,
    IdempotencyRecord,
    IdempotencyStatus,
    LearningEvidence,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection
from app.features.post_trade.application.handoff_service import Ft012Handoff

NOW = datetime(2026, 8, 27, 14, 0, tzinfo=UTC)
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
TRADE_ID = UUID("00000000-0000-4000-8000-000000000002")
OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000003")
REVIEW_ID = UUID("00000000-0000-4000-8000-000000000004")
VERSION_ID = UUID("00000000-0000-4000-8000-000000000005")


class FixedClock:
    def now(self) -> datetime:
        return NOW


class UuidFactory:
    def new_uuid(self) -> UUID:
        return uuid4()


class FakeIdempotencyRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[UUID, str, str], IdempotencyRecord] = {}

    async def get(self, workspace_id: UUID, command_type: str, key: str):
        return self.records.get((workspace_id, command_type, key))

    async def add(self, record: IdempotencyRecord) -> None:
        self.records[(record.workspace_id, record.command_type, record.idempotency_key)] = record

    async def mark_succeeded(
        self,
        *,
        record_id: UUID,
        result_type: str,
        result_id: UUID,
        completed_at: datetime,
    ) -> None:
        for key, record in tuple(self.records.items()):
            if record.id == record_id:
                self.records[key] = replace(
                    record,
                    status=IdempotencyStatus.SUCCEEDED,
                    result_type=result_type,
                    result_id=result_id,
                    completed_at=completed_at,
                )
                return
        raise AssertionError("idempotency record missing")

    async def mark_failed_final(self, **_: object) -> None:
        raise AssertionError("not expected")


class FakeUow:
    def __init__(self) -> None:
        self.idempotency_records = FakeIdempotencyRepository()
        self.flush_count = 0
        self.rollback_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flush_count += 1

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        self.rollback_count += 1


class FakeRepository:
    def __init__(self) -> None:
        self.projection: LearningEvidenceProjection | None = None
        self.pending_evidence: LearningEvidence | None = None

    async def get_by_source(self, *, workspace_id: UUID, exit_review_version_id: UUID):
        projection = self.projection
        if projection is None:
            return None
        source = projection.source
        if (
            projection.evidence.workspace_id == workspace_id
            and isinstance(source, FT011Evidence)
            and source.exit_review_version_id == exit_review_version_id
        ):
            return projection
        return None

    async def get_by_evidence_id(self, *, workspace_id: UUID, evidence_id: UUID):
        projection = self.projection
        if (
            projection is not None
            and projection.evidence.workspace_id == workspace_id
            and projection.evidence.id == evidence_id
        ):
            return projection
        return None

    async def add_evidence(self, evidence: LearningEvidence) -> None:
        self.pending_evidence = evidence

    async def add_source(self, source: FT011Evidence) -> None:
        assert self.pending_evidence is not None
        self.projection = LearningEvidenceProjection(
            evidence=self.pending_evidence,
            source=source,
        )


class FakeHandoffReader:
    def __init__(self, handoff: Ft012Handoff) -> None:
        self.handoff = handoff
        self.calls = 0

    async def get(self, *, workspace_id: UUID, trade_id: UUID) -> Ft012Handoff:
        assert workspace_id == WORKSPACE_ID
        assert trade_id == TRADE_ID
        self.calls += 1
        return self.handoff


def _ready_handoff() -> Ft012Handoff:
    return Ft012Handoff(
        ready=True,
        reason="READY",
        post_trade_observation_id=OBSERVATION_ID,
        exit_review_id=REVIEW_ID,
        exit_review_version_id=VERSION_ID,
    )


def _service(uow: FakeUow, repository: FakeRepository, reader: FakeHandoffReader):
    return MaterializeFt011LearningEvidenceService(
        uow=uow,
        repository=repository,
        handoff_reader=reader,
        clock=FixedClock(),
        id_factory=UuidFactory(),
    )


def test_request_fingerprint_is_deterministic_and_source_scoped() -> None:
    first = request_fingerprint(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)
    second = request_fingerprint(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)
    other = request_fingerprint(workspace_id=WORKSPACE_ID, trade_id=uuid4())

    assert first == second
    assert first != other
    assert len(first) == 64


async def test_materializes_complete_ft011_provenance() -> None:
    uow = FakeUow()
    repository = FakeRepository()
    reader = FakeHandoffReader(_ready_handoff())

    result = await _service(uow, repository, reader).execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="request-1",
    )

    assert result.created is True
    assert result.replayed is False
    assert result.exit_review_version_id == VERSION_ID
    assert repository.projection is not None
    assert repository.projection.evidence.id == result.learning_evidence_id
    source = repository.projection.source
    assert isinstance(source, FT011Evidence)
    assert source.trade_id == TRADE_ID
    assert source.post_trade_observation_id == OBSERVATION_ID
    assert source.exit_review_id == REVIEW_ID
    assert source.exit_review_version_id == VERSION_ID


async def test_same_request_replays_pinned_evidence_without_rechecking_ft011() -> None:
    uow = FakeUow()
    repository = FakeRepository()
    reader = FakeHandoffReader(_ready_handoff())
    service = _service(uow, repository, reader)

    created = await service.execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="request-1",
    )
    replayed = await service.execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="request-1",
    )

    assert replayed.learning_evidence_id == created.learning_evidence_id
    assert replayed.exit_review_version_id == VERSION_ID
    assert replayed.created is False
    assert replayed.replayed is True
    assert reader.calls == 1


async def test_different_key_same_source_returns_existing_semantic_evidence() -> None:
    uow = FakeUow()
    repository = FakeRepository()
    reader = FakeHandoffReader(_ready_handoff())
    service = _service(uow, repository, reader)

    created = await service.execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="request-1",
    )
    existing = await service.execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="request-2",
    )

    assert existing.learning_evidence_id == created.learning_evidence_id
    assert existing.created is False
    assert existing.replayed is False
    assert len(uow.idempotency_records.records) == 2


async def test_not_ready_fails_closed_without_idempotency_success() -> None:
    uow = FakeUow()
    repository = FakeRepository()
    reader = FakeHandoffReader(
        Ft012Handoff(
            ready=False,
            reason="EXIT_REVIEW_STALE",
            post_trade_observation_id=OBSERVATION_ID,
            exit_review_id=REVIEW_ID,
            exit_review_version_id=VERSION_ID,
        )
    )

    with pytest.raises(Ft011MaterializationError) as error:
        await _service(uow, repository, reader).execute(
            workspace_id=WORKSPACE_ID,
            trade_id=TRADE_ID,
            idempotency_key="request-1",
        )

    assert error.value.code is Ft011MaterializationErrorCode.SOURCE_NOT_READY
    assert error.value.source_reason == "EXIT_REVIEW_STALE"
    assert uow.idempotency_records.records == {}
    assert repository.projection is None


async def test_same_key_different_source_identity_is_rejected() -> None:
    uow = FakeUow()
    repository = FakeRepository()
    reader = FakeHandoffReader(_ready_handoff())
    uow.idempotency_records.records[(WORKSPACE_ID, COMMAND_TYPE, "request-1")] = IdempotencyRecord(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        command_type=COMMAND_TYPE,
        idempotency_key="request-1",
        request_fingerprint=request_fingerprint(workspace_id=WORKSPACE_ID, trade_id=uuid4()),
        status=IdempotencyStatus.IN_PROGRESS,
        created_at=NOW,
    )

    with pytest.raises(Ft011MaterializationError) as error:
        await _service(uow, repository, reader).execute(
            workspace_id=WORKSPACE_ID,
            trade_id=TRADE_ID,
            idempotency_key="request-1",
        )

    assert error.value.code is Ft011MaterializationErrorCode.IDEMPOTENCY_KEY_REUSED
    assert reader.calls == 0
