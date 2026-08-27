from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.learning.application.ft011_materialization_service import (
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
    MaterializeFt011LearningEvidenceService,
)
from app.features.learning.domain import FT011Evidence, LearningEvidence
from app.features.learning.persistence.repositories import LearningEvidenceProjection
from app.features.post_trade.application.handoff_service import Ft012Handoff

NOW = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
TRADE_ID = uuid4()
VERSION_ID = uuid4()


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class IdempotencyRepo:
    def __init__(self) -> None:
        self.record = None

    async def get(self, workspace_id, command_type, key):
        del workspace_id, command_type, key
        return None

    async def add(self, record) -> None:
        self.record = record

    async def mark_succeeded(self, **kwargs) -> None:
        del kwargs


class Uow:
    def __init__(self, *, fail_flush: int | None = None) -> None:
        self.idempotency_records = IdempotencyRepo()
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0
        self.fail_flush = fail_flush

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        del exc, traceback
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        self.flushes += 1
        if self.fail_flush == self.flushes:
            raise IntegrityError("insert", {}, RuntimeError("unique violation"))

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class Repository:
    def __init__(self) -> None:
        self.evidence: LearningEvidence | None = None
        self.source: FT011Evidence | None = None

    async def get_by_source(self, **kwargs):
        del kwargs
        return None

    async def get_by_evidence_id(self, **kwargs):
        del kwargs
        if self.evidence is None or self.source is None:
            return None
        return LearningEvidenceProjection(evidence=self.evidence, source=self.source)

    async def add_evidence(self, evidence: LearningEvidence) -> None:
        self.evidence = evidence

    async def add_source(self, source: FT011Evidence) -> None:
        self.source = source


class Handoff:
    async def get(self, **kwargs) -> Ft012Handoff:
        del kwargs
        return Ft012Handoff(
            ready=True,
            reason="READY",
            post_trade_observation_id=uuid4(),
            exit_review_id=uuid4(),
            exit_review_version_id=VERSION_ID,
        )


def service(uow: Uow, repository: Repository) -> MaterializeFt011LearningEvidenceService:
    return MaterializeFt011LearningEvidenceService(
        uow=uow,  # type: ignore[arg-type]
        repository=repository,
        handoff_reader=Handoff(),
        clock=Clock(),
        id_factory=Ids(),
    )


async def test_successful_materialization_commits_after_success_record() -> None:
    uow = Uow()
    repository = Repository()

    result = await service(uow, repository).execute(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        idempotency_key="tx-1",
    )

    assert result.created is True
    assert uow.flushes == 4
    assert uow.commits == 1
    assert uow.rollbacks == 0


async def test_semantic_uniqueness_race_rolls_back_without_commit() -> None:
    uow = Uow(fail_flush=3)
    repository = Repository()

    with pytest.raises(Ft011MaterializationError) as error:
        await service(uow, repository).execute(
            workspace_id=WORKSPACE_ID,
            trade_id=TRADE_ID,
            idempotency_key="tx-race",
        )

    assert error.value.code is Ft011MaterializationErrorCode.MATERIALIZATION_CONFLICT
    assert uow.commits == 0
    assert uow.rollbacks >= 1
