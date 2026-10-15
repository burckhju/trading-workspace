"""Today's qualified source read is separate from the immutable lesson snapshot."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from test_explicit_review_commands import NOW

from app.features.learning.application.lesson_review_query import LessonReviewQuery
from app.features.learning.application.lesson_review_commands import ReviewCommandError
from app.features.learning.domain import (
    FT011Evidence,
    TradeJournalVersionEvidence,
    ExternalObservationEvidence,
    ExternalObservationJournalVersionEvidence,
    LearningEvidence,
    LearningEvidenceType,
    JournalVersionStatus,
)
from app.features.post_trade.domain import ExitReviewCurrentness


def build(kind):
    eid, vid, wid = uuid4(), uuid4(), uuid4()
    sources = {
        LearningEvidenceType.FT011: FT011Evidence(eid, uuid4(), uuid4(), uuid4(), vid),
        LearningEvidenceType.TRADE_JOURNAL_VERSION: TradeJournalVersionEvidence(eid, vid),
        LearningEvidenceType.EXTERNAL_OBSERVATION: ExternalObservationEvidence(eid, vid),
        LearningEvidenceType.EXTERNAL_OBSERVATION_JOURNAL_VERSION: ExternalObservationJournalVersionEvidence(
            eid, vid
        ),
    }
    uow = SimpleNamespace(
        learning_evidence=SimpleNamespace(
            get=AsyncMock(
                return_value=SimpleNamespace(
                    source=sources[kind], evidence=LearningEvidence(eid, wid, kind, NOW)
                )
            )
        ),
        commit=AsyncMock(),
        flush=AsyncMock(),
    )
    inspector = SimpleNamespace(
        inspect_version_currentness=AsyncMock(return_value=ExitReviewCurrentness.STALE)
    )
    return (
        LessonReviewQuery(uow=uow, inspector=inspector, clock=SimpleNamespace(now=lambda: NOW)),
        uow,
        inspector,
        eid,
        vid,
        wid,
    )


@pytest.mark.parametrize(
    "current", [None, ExitReviewCurrentness.CURRENT, ExitReviewCurrentness.STALE]
)
async def test_ft011_uses_exact_owner_inspection_without_any_writes(current):
    query, uow, inspector, eid, vid, wid = build(LearningEvidenceType.FT011)
    inspector.inspect_version_currentness.return_value = current
    value = await query.source(workspace_id=wid, evidence_id=eid)
    assert value.source_version_id == vid and value.source_currentness == (
        current.value if current else "UNKNOWN"
    )
    inspector.inspect_version_currentness.assert_awaited_once_with(workspace_id=wid, version_id=vid)
    uow.commit.assert_not_awaited()
    uow.flush.assert_not_awaited()


@pytest.mark.parametrize(
    "successor_status", [JournalVersionStatus.DRAFT, JournalVersionStatus.FINALIZED]
)
async def test_journal_supersession_and_review_staleness_remain_separate(successor_status):
    query, uow, inspector, eid, vid, wid = build(LearningEvidenceType.TRADE_JOURNAL_VERSION)
    rid, successor = uuid4(), uuid4()
    uow.journals = SimpleNamespace(
        origin=AsyncMock(return_value=SimpleNamespace(id=uuid4())),
        versions=AsyncMock(
            return_value=[
                SimpleNamespace(id=successor, version=2, status=successor_status),
                SimpleNamespace(
                    id=vid,
                    version=1,
                    status=JournalVersionStatus.FINALIZED,
                    source_exit_review_version_id=rid,
                ),
            ]
        ),
    )
    value = await query.source(workspace_id=wid, evidence_id=eid)
    assert value.source_currentness == (
        "SUPERSEDED" if successor_status is JournalVersionStatus.FINALIZED else "CURRENT"
    )
    assert (
        value.review_currentness == "STALE"
        and value.source_version_id == vid
        and value.checked_at == NOW
    )
    assert value.superseded_by_version_id == (
        successor if successor_status is JournalVersionStatus.FINALIZED else None
    )
    inspector.inspect_version_currentness.assert_awaited_once_with(workspace_id=wid, version_id=rid)
    uow.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "own,current_exists,same",
    [(True, True, True), (True, True, False), (True, False, False), (False, True, False)],
)
async def test_external_observation_retains_exact_version_and_unknown(own, current_exists, same):
    query, uow, inspector, eid, vid, wid = build(LearningEvidenceType.EXTERNAL_OBSERVATION)
    uow.external_observations = SimpleNamespace(
        get=AsyncMock(return_value=object() if own else None)
    )
    uow.external_observation_versions = SimpleNamespace(
        get=AsyncMock(return_value=SimpleNamespace(external_observation_id=uuid4())),
        get_current=AsyncMock(
            return_value=SimpleNamespace(id=vid if same else uuid4()) if current_exists else None
        ),
    )
    value = await query.source(workspace_id=wid, evidence_id=eid)
    assert value.source_currentness == (
        "UNKNOWN" if not own or not current_exists else "CURRENT" if same else "SUPERSEDED"
    )
    assert value.source_version_id == vid
    inspector.inspect_version_currentness.assert_not_awaited()


async def test_external_journal_without_qualified_reader_is_unknown_not_current():
    query, uow, _, eid, vid, wid = build(LearningEvidenceType.EXTERNAL_OBSERVATION_JOURNAL_VERSION)
    value = await query.source(workspace_id=wid, evidence_id=eid)
    assert (
        value.source_version_id == vid
        and value.source_currentness == "UNKNOWN"
        and value.review_currentness is None
    )
    uow.commit.assert_not_awaited()


async def test_missing_cross_workspace_evidence_and_failed_owner_are_not_zero_or_current():
    query, uow, inspector, eid, _, wid = build(LearningEvidenceType.FT011)
    inspector.inspect_version_currentness.side_effect = RuntimeError("source read failed")
    with pytest.raises(RuntimeError):
        await query.source(workspace_id=wid, evidence_id=eid)
    uow.learning_evidence.get.return_value = None
    with pytest.raises(ReviewCommandError, match="not found"):
        await query.source(workspace_id=wid, evidence_id=eid)


async def test_context_sorts_history_without_changing_current_pointer_or_writing():
    from dataclasses import replace
    from test_explicit_review_commands import Uow

    uow = Uow()
    lesson = uow.state["lesson"]
    old = uow.state["versions"][lesson.current_version_id]
    new = replace(old, id=uuid4(), version=2, supersedes_version_id=old.id)
    uow.state["versions"][new.id] = new
    uow.state["links"][new.id] = ()
    uow.state["lesson"] = replace(lesson, current_version_id=new.id)
    uow.lesson_versions.list_for_lesson = AsyncMock(return_value=(old, new))
    uow.lesson_review_signals.list_for_lesson = AsyncMock(return_value=())
    uow.lesson_state_transitions.list_for_lesson = AsyncMock(return_value=())
    query = LessonReviewQuery(
        uow=uow, inspector=SimpleNamespace(), clock=SimpleNamespace(now=lambda: NOW)
    )
    result = await query.context(workspace_id=lesson.workspace_id, lesson_id=lesson.id)
    assert [item.version.id for item in result.history] == [new.id, old.id]
    assert result.lesson.current_version_id == new.id and result.read_at == NOW
    assert result.history[1].evidence_links == uow.state["links"][old.id]
    uow.flush.assert_not_awaited()
    assert uow.commits == 0
    with pytest.raises(ReviewCommandError):
        await query.context(workspace_id=uuid4(), lesson_id=lesson.id)
