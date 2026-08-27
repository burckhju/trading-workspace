from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.learning.application.ft011_materialization_status_service import (
    Ft011MaterializationStatusService,
)
from app.features.learning.domain import FT011Evidence, LearningEvidence, LearningEvidenceType
from app.features.learning.persistence.repositories import LearningEvidenceProjection
from app.features.post_trade.application.handoff_service import Ft012Handoff

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
TRADE_ID = uuid4()
VERSION_ID = uuid4()


class HandoffReader:
    def __init__(self, handoff: Ft012Handoff) -> None:
        self.handoff = handoff

    async def get(self, **kwargs) -> Ft012Handoff:
        del kwargs
        return self.handoff


class Repository:
    def __init__(self, projection: LearningEvidenceProjection | None = None) -> None:
        self.projection = projection
        self.source_calls: list[dict[str, object]] = []

    async def get_by_source(self, **kwargs):
        self.source_calls.append(kwargs)
        return self.projection

    async def get_by_evidence_id(self, **kwargs):
        del kwargs
        return None

    async def add_evidence(self, evidence) -> None:
        del evidence

    async def add_source(self, source) -> None:
        del source


def ready_handoff() -> Ft012Handoff:
    return Ft012Handoff(
        ready=True,
        reason="READY",
        post_trade_observation_id=uuid4(),
        exit_review_id=uuid4(),
        exit_review_version_id=VERSION_ID,
    )


async def test_status_reports_not_ready_without_ft012_lookup() -> None:
    repository = Repository()
    service = Ft011MaterializationStatusService(
        repository=repository,
        handoff_reader=HandoffReader(
            Ft012Handoff(
                ready=False,
                reason="EXIT_REVIEW_NOT_FINALIZED",
                post_trade_observation_id=None,
                exit_review_id=None,
                exit_review_version_id=None,
            )
        ),
    )

    result = await service.get(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)

    assert result.ready is False
    assert result.materialized is False
    assert result.reason == "EXIT_REVIEW_NOT_FINALIZED"
    assert repository.source_calls == []


async def test_status_reports_ready_not_materialized_for_current_version() -> None:
    repository = Repository()
    service = Ft011MaterializationStatusService(
        repository=repository,
        handoff_reader=HandoffReader(ready_handoff()),
    )

    result = await service.get(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)

    assert result.ready is True
    assert result.materialized is False
    assert result.exit_review_version_id == VERSION_ID
    assert repository.source_calls[0]["exit_review_version_id"] == VERSION_ID


async def test_status_reports_materialized_evidence_for_current_version() -> None:
    evidence_id = uuid4()
    projection = LearningEvidenceProjection(
        evidence=LearningEvidence(
            id=evidence_id,
            workspace_id=WORKSPACE_ID,
            evidence_type=LearningEvidenceType.FT011,
            created_at=datetime(2026, 8, 27, 21, 0, tzinfo=UTC),
        ),
        source=FT011Evidence(
            learning_evidence_id=evidence_id,
            trade_id=TRADE_ID,
            post_trade_observation_id=uuid4(),
            exit_review_id=uuid4(),
            exit_review_version_id=VERSION_ID,
        ),
    )
    service = Ft011MaterializationStatusService(
        repository=Repository(projection),
        handoff_reader=HandoffReader(ready_handoff()),
    )

    result = await service.get(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)

    assert result.ready is True
    assert result.materialized is True
    assert result.learning_evidence_id == evidence_id
    assert result.exit_review_version_id == VERSION_ID
