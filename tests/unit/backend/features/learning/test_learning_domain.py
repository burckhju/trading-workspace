from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.features.learning.domain import (
    IdempotencyRecord,
    IdempotencyStatus,
    JournalVersionStatus,
    Lesson,
    LessonEvidenceRelation,
    LessonState,
    TradeJournalVersion,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def test_lesson_evidence_relation_includes_contextual() -> None:
    assert LessonEvidenceRelation.CONTEXTUAL.value == "CONTEXTUAL"


def test_trade_journal_draft_rejects_finalization_metadata() -> None:
    with pytest.raises(ValueError):
        TradeJournalVersion(
            id=uuid4(),
            trade_journal_id=uuid4(),
            version=1,
            status=JournalVersionStatus.DRAFT,
            what_went_well=None,
            would_do_differently=None,
            additional_notes=None,
            created_at=NOW,
            created_by=uuid4(),
            updated_at=NOW,
            updated_by=uuid4(),
            finalized_at=NOW,
            finalized_by=uuid4(),
        )


def test_trade_journal_finalize_preserves_reflection() -> None:
    value = TradeJournalVersion(
        id=uuid4(),
        trade_journal_id=uuid4(),
        version=1,
        status=JournalVersionStatus.DRAFT,
        what_went_well="discipline",
        would_do_differently="wait",
        additional_notes="note",
        created_at=NOW,
        created_by=uuid4(),
        updated_at=NOW,
        updated_by=uuid4(),
    )
    result = value.finalize(finalized_at=NOW + timedelta(minutes=1), finalized_by=uuid4())
    assert result.status is JournalVersionStatus.FINALIZED
    assert result.what_went_well == "discipline"
    assert result.would_do_differently == "wait"
    assert result.additional_notes == "note"


def test_lesson_title_must_be_nonblank() -> None:
    with pytest.raises(ValueError):
        Lesson(
            id=uuid4(),
            workspace_id=uuid4(),
            title=" ",
            current_version_id=uuid4(),
            current_state=LessonState.CURRENT,
            created_at=NOW,
            created_by=uuid4(),
            updated_at=NOW,
            updated_by=uuid4(),
        )


def test_idempotency_in_progress_rejects_terminal_metadata() -> None:
    with pytest.raises(ValueError):
        IdempotencyRecord(
            id=uuid4(),
            workspace_id=uuid4(),
            command_type="execute_external_observation",
            idempotency_key="abc",
            request_fingerprint="x" * 64,
            status=IdempotencyStatus.IN_PROGRESS,
            created_at=NOW,
            error_code="FINAL",
        )
