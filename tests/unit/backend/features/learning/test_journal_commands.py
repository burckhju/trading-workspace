"""Application contracts; PostgreSQL constraints have separate real-database tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.learning.application.journal_service import (
    JournalCommand,
    JournalError,
    JournalService,
)
from app.features.learning.application.journal_service import (
    JournalOperation as Op,
)
from app.features.learning.domain import IdempotencyStatus, JournalVersionStatus
from app.features.post_trade.application.handoff_service import Ft012Handoff
from app.features.post_trade.domain import ExitReviewCurrentness

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


@pytest.fixture
def graph():
    ws, trade, actor, review = uuid4(), uuid4(), uuid4(), uuid4()
    data = SimpleNamespace(journal=None, versions={}, evidence={}, records={}, state="CURRENT")
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.flush = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    async def add(journal):
        data.journal = journal

    async def add_version(version):
        data.versions[version.id] = version

    async def replace_draft(version, expected):
        if data.versions[version.id].edit_revision != expected:
            return False
        data.versions[version.id] = version
        return True

    async def evidence(w, v, e, at):
        data.evidence[v] = e

    async def record(r):
        data.records[(r.command_type, r.idempotency_key)] = r

    async def succeed(**kw):
        r = next(r for r in data.records.values() if r.id == kw["record_id"])
        data.records[(r.command_type, r.idempotency_key)] = replace(
            r,
            status=IdempotencyStatus.SUCCEEDED,
            result_type=kw["result_type"],
            result_id=kw["result_id"],
            completed_at=kw["completed_at"],
        )

    uow.journals = SimpleNamespace(
        get=AsyncMock(side_effect=lambda w, t: data.journal if w == ws and t == trade else None),
        versions=AsyncMock(
            side_effect=lambda j: tuple(
                sorted(data.versions.values(), key=lambda v: v.version, reverse=True)
            )
        ),
        add=AsyncMock(side_effect=add),
        add_version=AsyncMock(side_effect=add_version),
        replace_draft=AsyncMock(side_effect=replace_draft),
        evidence_id=AsyncMock(side_effect=lambda v: data.evidence.get(v)),
        add_evidence=AsyncMock(side_effect=evidence),
        origin=AsyncMock(
            side_effect=lambda w, v: data.journal if w == ws and v in data.versions else None
        ),
    )
    uow.idempotency_records = SimpleNamespace(
        get=AsyncMock(side_effect=lambda w, c, k: data.records.get((c, k))),
        add=AsyncMock(side_effect=record),
        mark_succeeded=AsyncMock(side_effect=succeed),
    )
    handoff = SimpleNamespace(
        get=AsyncMock(return_value=Ft012Handoff(True, "READY", uuid4(), uuid4(), review))
    )
    inspector = SimpleNamespace(
        inspect_version_currentness=AsyncMock(
            side_effect=lambda **kw: (
                ExitReviewCurrentness(data.state) if data.state != "UNKNOWN" else None
            )
        )
    )
    reader = SimpleNamespace(get=AsyncMock(return_value=object()))
    service = JournalService(
        uow=uow,
        trade_reader=reader,
        handoff_reader=handoff,
        inspector=inspector,
        clock=SimpleNamespace(now=lambda: NOW),
        id_factory=SimpleNamespace(new_uuid=uuid4),
    )

    async def run(command, key=None, actor_id=actor):
        return await service.execute(
            workspace_id=ws,
            trade_id=trade,
            actor_id=actor_id,
            command=command,
            idempotency_key=key if key is not None else str(uuid4()),
        )

    return SimpleNamespace(**locals())


def create(g, **kw):
    return JournalCommand(Op.CREATE_DRAFT, expected_exit_review_version_id=g.review, **kw)


@pytest.mark.asyncio
async def test_empty_draft_final_receipt_successor_and_evidence_stay_separate(graph):
    g = graph
    first = await g.run(create(g), "create")
    replay = await g.run(create(g), "create")
    assert replay.replayed and replay.result_id == first.result_id
    draft = g.data.versions[first.result_id]
    assert draft.what_went_well is None and draft.edit_revision == 1
    assert not g.data.evidence
    final_cmd = JournalCommand(
        Op.FINALIZE,
        version_id=draft.id,
        expected_edit_revision=1,
        expected_exit_review_version_id=g.review,
    )
    await g.run(final_cmd, "finish")
    final = g.data.versions[draft.id]
    assert final.status is JournalVersionStatus.FINALIZED and final.edit_revision == 2
    assert final.source_exit_review_version_id == g.review
    assert not g.data.evidence
    successor = await g.run(create(g, expected_latest_version_id=final.id))
    assert g.data.versions[successor.result_id].supersedes_version_id == final.id
    assert g.data.versions[final.id] == final
    assert (await g.run(final_cmd, "finish")).replayed  # not a mutable content replay
    materialize = JournalCommand(Op.MATERIALIZE, version_id=final.id)
    g.data.state = "STALE"
    e = await g.run(materialize, "evidence")
    assert (await g.run(materialize, "evidence")).replayed
    assert (await g.run(materialize, "different")).result_id == e.result_id
    assert len(g.data.evidence) == 1
    history = await g.service.history(workspace_id=g.ws, trade_id=g.trade)
    assert history.versions[-1].version == final
    assert history.versions[-1].source_currentness == "STALE"
    assert history.handoff.ready is False
    assert history.versions[-1].learning_evidence_id == e.result_id
    exact = await g.service.version(workspace_id=g.ws, version_id=final.id)
    assert len(exact.versions) == 1 and not exact.versions[0].is_latest


@pytest.mark.asyncio
async def test_save_cas_replay_and_explicit_source_rebind(graph):
    g = graph
    draft_id = (await g.run(create(g))).result_id
    save = JournalCommand(
        Op.SAVE_DRAFT,
        version_id=draft_id,
        expected_edit_revision=1,
        what_went_well="eigene Interpretation",
        additional_notes="",
    )
    await g.run(save, "save")
    assert (await g.run(save, "save")).replayed
    assert g.data.versions[draft_id].edit_revision == 2
    with pytest.raises(JournalError, match="Saved draft"):
        await g.run(replace(save, additional_notes="anderer Tab"))
    g.data.state = "STALE"
    await g.run(replace(save, expected_edit_revision=2, additional_notes="Ergänzung trotz Stale"))
    with pytest.raises(JournalError) as error:
        await g.run(
            JournalCommand(
                Op.FINALIZE,
                version_id=draft_id,
                expected_edit_revision=3,
                expected_exit_review_version_id=g.review,
            )
        )
    assert error.value.code == "JOURNAL_SOURCE_NOT_READY"
    next_review = uuid4()
    g.handoff.get.return_value = replace(
        g.handoff.get.return_value, exit_review_version_id=next_review
    )
    g.data.state = "CURRENT"
    with pytest.raises(JournalError) as mismatch:
        await g.run(
            JournalCommand(
                Op.FINALIZE,
                version_id=draft_id,
                expected_edit_revision=3,
                expected_exit_review_version_id=next_review,
            )
        )
    assert mismatch.value.code == "SOURCE_VERSION_MISMATCH"
    await g.run(
        JournalCommand(
            Op.REBIND_SOURCE,
            version_id=draft_id,
            expected_edit_revision=3,
            expected_exit_review_version_id=next_review,
        )
    )
    assert g.data.versions[draft_id].source_exit_review_version_id == next_review
    assert g.data.versions[draft_id].additional_notes == "Ergänzung trotz Stale"


@pytest.mark.parametrize("state", ["STALE", "UNKNOWN"])
@pytest.mark.asyncio
async def test_unqualified_current_source_creates_nothing(graph, state):
    g = graph
    g.data.state = state
    with pytest.raises(JournalError) as exc:
        await g.run(create(g))
    assert exc.value.code == "JOURNAL_SOURCE_NOT_READY"
    g.uow.journals.add.assert_not_awaited()
    g.uow.commit.assert_not_awaited()


@pytest.mark.parametrize("key", ["", " ", "a" * 241])
@pytest.mark.asyncio
async def test_invalid_keys_fail_before_trade_read(graph, key):
    with pytest.raises(JournalError) as exc:
        await graph.run(create(graph), key)
    assert exc.value.code == "JOURNAL_INVALID_REQUEST"
    graph.reader.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_cancelled_trade_wrong_version_actor_and_double_create(graph):
    g = graph
    g.reader.get.return_value = None
    with pytest.raises(JournalError) as exc:
        await g.run(create(g))
    assert exc.value.code == "JOURNAL_NOT_FOUND"
    g.reader.get.return_value = object()
    with pytest.raises(JournalError) as exc:
        await g.run(replace(create(g), expected_exit_review_version_id=uuid4()))
    assert exc.value.code == "SOURCE_VERSION_MISMATCH"
    await g.run(create(g), "once")
    with pytest.raises(JournalError) as exc:
        await g.run(create(g), "once", actor_id=uuid4())
    assert exc.value.code == "IDEMPOTENCY_KEY_REUSED"
    with pytest.raises(JournalError):
        await g.run(create(g))
    with pytest.raises(JournalError):
        await g.service.version(workspace_id=uuid4(), version_id=next(iter(g.data.versions)))


@pytest.mark.asyncio
async def test_read_only_history_keeps_unknown_legacy_source_and_propagates_read_failure(graph):
    g = graph
    v = (await g.run(create(g))).result_id
    g.data.versions[v] = replace(g.data.versions[v], source_exit_review_version_id=None)
    g.uow.commit.reset_mock()
    h = await g.service.history(workspace_id=g.ws, trade_id=g.trade)
    assert h.versions[0].source_currentness == "UNKNOWN"
    g.uow.commit.assert_not_awaited()
    g.uow.journals.get.side_effect = RuntimeError("read unavailable")
    with pytest.raises(RuntimeError):
        await g.service.history(workspace_id=g.ws, trade_id=g.trade)


@pytest.mark.asyncio
async def test_draft_is_not_evidence_and_cas_or_integrity_failure_never_commits(graph):
    g = graph
    v = (await g.run(create(g))).result_id
    with pytest.raises(JournalError):
        await g.run(JournalCommand(Op.MATERIALIZE, version_id=v))
    g.uow.commit.reset_mock()
    g.uow.journals.replace_draft.side_effect = None
    g.uow.journals.replace_draft.return_value = False
    with pytest.raises(JournalError):
        await g.run(JournalCommand(Op.SAVE_DRAFT, version_id=v, expected_edit_revision=1))
    g.uow.commit.assert_not_awaited()
    g.uow.journals.replace_draft.side_effect = IntegrityError("synthetic", {}, Exception())
    with pytest.raises(JournalError) as error:
        await g.run(JournalCommand(Op.SAVE_DRAFT, version_id=v, expected_edit_revision=1))
    assert error.value.code == "JOURNAL_CONFLICT"
    g.uow.rollback.assert_awaited_once()
    g.uow.commit.assert_not_awaited()


def test_domain_monotonic_audit_and_final_immutability(graph):
    from app.features.learning.domain import TradeJournalVersion

    g = graph
    v = TradeJournalVersion(
        uuid4(),
        uuid4(),
        1,
        JournalVersionStatus.DRAFT,
        None,
        None,
        None,
        NOW,
        g.actor,
        NOW,
        g.actor,
    )
    with pytest.raises(ValueError):
        replace(v, edit_revision=0)
    later = v.replace_draft_content(
        what_went_well=None,
        would_do_differently="",
        additional_notes=None,
        updated_at=NOW + timedelta(seconds=1),
        updated_by=g.actor,
    )
    with pytest.raises(ValueError):
        later.finalize(finalized_at=NOW, finalized_by=g.actor)
    with pytest.raises(ValueError):
        later.replace_draft_content(
            what_went_well=None,
            would_do_differently=None,
            additional_notes=None,
            updated_at=NOW,
            updated_by=g.actor,
        )
    final = later.finalize(finalized_at=NOW + timedelta(seconds=2), finalized_by=g.actor)
    with pytest.raises(ValueError):
        final.finalize(finalized_at=NOW + timedelta(seconds=3), finalized_by=g.actor)
    with pytest.raises(ValueError):
        final.replace_draft_content(
            what_went_well=None,
            would_do_differently=None,
            additional_notes=None,
            updated_at=NOW + timedelta(seconds=3),
            updated_by=g.actor,
        )
