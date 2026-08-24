from datetime import UTC, datetime
from uuid import uuid4

from app.features.learning.domain import LearningEvidence, LearningEvidenceType


def test_learning_evidence_types_are_exact() -> None:
    assert {value.value for value in LearningEvidenceType} == {
        "FT011",
        "TRADE_JOURNAL_VERSION",
        "EXTERNAL_OBSERVATION",
        "EXTERNAL_OBSERVATION_JOURNAL_VERSION",
    }


def test_learning_evidence_anchor_is_typed() -> None:
    value = LearningEvidence(
        id=uuid4(),
        workspace_id=uuid4(),
        evidence_type=LearningEvidenceType.FT011,
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert value.evidence_type is LearningEvidenceType.FT011
