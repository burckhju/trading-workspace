"""Application semantics with a transactional fake; PostgreSQL tests prove actual locks."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.learning.application.lesson_review_commands import (
    LessonReviewCommand,
    LessonReviewCommands,
    ReviewCommandError,
    ReviewOperation,
)
from app.features.learning.application.lesson_review_service import LessonReviewServiceError
from app.features.learning.application.lesson_service import LessonEvidenceInput, LessonServiceError
from app.features.learning.domain import (
    IdempotencyStatus,
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonReviewSignalStatus,
    LessonState,
    LessonVersion,
)

NOW = datetime(2026, 10, 15, tzinfo=UTC)


class Uow:
    def __init__(self):
        actor, workspace, lid, vid = (uuid4() for _ in range(4))
        self.state = dict(
            lesson=Lesson(
                lid, workspace, "Explicit", vid, LessonState.CURRENT, NOW, actor, NOW, actor
            ),
            versions={
                vid: LessonVersion(
                    vid, lid, 1, "Process", "Original personal interpretation", NOW, actor
                )
            },
            links={
                vid: tuple(
                    LessonEvidenceLink(uuid4(), vid, uuid4(), r, NOW, actor)
                    for r in (LessonEvidenceRelation.SUPPORTS, LessonEvidenceRelation.CONTRADICTS)
                )
            },
            signals={},
            triggers={},
            transitions=[],
            receipts={},
        )
        self.known = {link.learning_evidence_id for link in self.state["links"][vid]}
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = False
        self.lessons = SimpleNamespace(
            lock=AsyncMock(side_effect=self.lock),
            get=AsyncMock(side_effect=self.get),
            transition_state=AsyncMock(side_effect=self.transition),
            advance_current=AsyncMock(side_effect=self.advance),
        )
        self.lesson_versions = SimpleNamespace(
            get=AsyncMock(side_effect=lambda vid: self.state["versions"].get(vid)),
            next_version_number=AsyncMock(side_effect=lambda *_: len(self.state["versions"]) + 1),
            add=AsyncMock(side_effect=self.add_version),
        )
        self.lesson_evidence_links = SimpleNamespace(
            list_for_version=AsyncMock(side_effect=lambda vid: self.state["links"][vid]),
            add_snapshot=AsyncMock(side_effect=self.snapshot),
        )
        self.learning_evidence = SimpleNamespace(
            get=AsyncMock(
                side_effect=lambda w, e: object() if w == workspace and e in self.known else None
            )
        )
        self.lesson_state_transitions = SimpleNamespace(
            add=AsyncMock(side_effect=self.state_transition)
        )
        self.lesson_review_signals = SimpleNamespace(
            get_open_for_lesson=AsyncMock(side_effect=self.open_signal),
            add_open=AsyncMock(side_effect=self.add_signal),
            get=AsyncMock(side_effect=lambda sid: self.state["signals"].get(sid)),
            resolve=AsyncMock(side_effect=self.resolve),
        )
        self.idempotency_records = SimpleNamespace(
            get=AsyncMock(side_effect=lambda w, c, k: self.state["receipts"].get((w, c, k))),
            add=AsyncMock(side_effect=self.add_receipt),
            mark_succeeded=AsyncMock(side_effect=self.succeed),
        )
        self.flush = AsyncMock()

    def lock(self, w, lesson_ref):
        return self.state["lesson"].workspace_id == w and self.state["lesson"].id == lesson_ref

    def get(self, w, lesson_ref):
        return self.state["lesson"] if self.lock(w, lesson_ref) else None

    def transition(self, **kw):
        assert self.state["lesson"].current_state == kw["expected_state"]
        self.state["lesson"] = replace(self.state["lesson"], current_state=kw["new_state"])
        return True

    def advance(self, **kw):
        assert self.state["lesson"].current_version_id == kw["expected_current_version_id"]
        self.state["lesson"] = replace(
            self.state["lesson"],
            current_state=kw["new_current_state"],
            current_version_id=kw["new_current_version_id"],
        )
        return True

    def add_version(self, v):
        self.state["versions"][v.id] = v

    def snapshot(self, vid, links):
        self.state["links"][vid] = links

    def state_transition(self, v):
        self.state["transitions"].append(v)

    def open_signal(self, lid):
        return next(
            (
                v
                for v in self.state["signals"].values()
                if v.lesson_id == lid and v.status is LessonReviewSignalStatus.OPEN
            ),
            None,
        )

    def add_signal(self, v, triggers):
        self.state["signals"][v.id] = v
        self.state["triggers"][v.id] = triggers

    def resolve(self, **kw):
        sid = kw.pop("signal_id")
        kw.pop("expected_status")
        self.state["signals"][sid] = replace(
            self.state["signals"][sid], status=LessonReviewSignalStatus.RESOLVED, **kw
        )
        return True

    def add_receipt(self, v):
        self.state["receipts"][(v.workspace_id, v.command_type, v.idempotency_key)] = v

    def succeed(self, **kw):
        key, v = next((k, v) for k, v in self.state["receipts"].items() if v.id == kw["record_id"])
        self.state["receipts"][key] = replace(
            v,
            status=IdempotencyStatus.SUCCEEDED,
            result_type=kw["result_type"],
            result_id=kw["result_id"],
            completed_at=kw["completed_at"],
        )

    async def __aenter__(self):
        self.before = deepcopy(self.state)
        return self

    async def __aexit__(self, typ, exc, tb):
        if typ:
            self.state = self.before
            self.rollbacks += 1

    async def commit(self):
        if self.fail_commit:
            raise RuntimeError("synthetic commit failure")
        self.commits += 1


@pytest.fixture
def graph():
    return Uow()


def cmd(u, operation="OPEN_SOURCE_REVIEW", **kwargs):
    lesson = u.state["lesson"]
    signal = u.open_signal(lesson.id)
    defaults = dict(
        operation=ReviewOperation(operation),
        expected_current_version_id=lesson.current_version_id,
        expected_current_state=lesson.current_state,
        expected_open_signal_id=signal.id if signal else None,
        reason="My explicit interpretation",
        reviewed_evidence_ids=tuple(
            link.learning_evidence_id for link in u.state["links"][lesson.current_version_id]
        ),
    )
    return LessonReviewCommand(**(defaults | kwargs))


async def execute(u, c, key="key", **kwargs):
    lesson_ref = u.state["lesson"]
    service = LessonReviewCommands(
        uow=u, clock=SimpleNamespace(now=lambda: NOW), id_factory=SimpleNamespace(new_uuid=uuid4)
    )
    return await service.execute(
        **(
            dict(
                workspace_id=lesson_ref.workspace_id,
                lesson_id=lesson_ref.id,
                actor_id=lesson_ref.created_by,
                idempotency_key=key,
                command=c,
            )
            | kwargs
        )
    )


async def test_source_open_and_unchanged_do_not_fabricate_contradiction_or_change_snapshots(graph):
    u = graph
    before = deepcopy(u.state)
    opening = cmd(u)
    receipt = await execute(u, opening)
    assert u.state["lesson"].current_state is LessonState.REVIEW_RECOMMENDED
    assert u.state["signals"] == {}
    assert (
        u.state["transitions"][0].related_lesson_version_id == opening.expected_current_version_id
    )
    assert u.state["transitions"][0].reason.startswith("SOURCE_REVIEW_OPENED: ")
    assert (await execute(u, opening)).result_id == receipt.result_id
    assert u.commits == 1
    await execute(u, cmd(u, "CONFIRM_UNCHANGED"), key="confirm")
    assert u.commits == 2 and u.state["lesson"].current_state is LessonState.CURRENT
    assert u.state["versions"] == before["versions"] and u.state["links"] == before["links"]
    replay = await execute(u, opening)
    assert replay.replayed and replay.result_id == receipt.result_id and u.commits == 2


@pytest.mark.parametrize(
    "change", ["version", "state", "signal", "workspace", "actor", "key-input"]
)
async def test_mismatched_pin_scope_or_receipt_is_rejected_before_changes(graph, change):
    u = graph
    c = cmd(u)
    kwargs = {}
    if change in ("actor", "key-input"):
        await execute(u, c)
        if change == "actor":
            kwargs["actor_id"] = uuid4()
        else:
            c = replace(c, reason="Other reason")
    elif change == "version":
        c = replace(c, expected_current_version_id=uuid4())
    elif change == "state":
        c = replace(c, expected_current_state=LessonState.RETIRED)
    elif change == "signal":
        c = replace(c, expected_open_signal_id=uuid4())
    else:
        kwargs["workspace_id"] = uuid4()
    before = deepcopy(u.state)
    with pytest.raises(ReviewCommandError):
        await execute(u, c, **kwargs)
    assert u.state == before


@pytest.mark.parametrize(
    "bad", ["none", "partial", "duplicate", "foreign", "empty-reason", "long-reason", "empty-key"]
)
async def test_open_requires_exact_complete_snapshot_and_nonblank_reason(graph, bad):
    u = graph
    c = cmd(u)
    key = "key"
    if bad == "none":
        c = replace(c, reviewed_evidence_ids=())
    elif bad == "partial":
        c = replace(c, reviewed_evidence_ids=c.reviewed_evidence_ids[:1])
    elif bad == "duplicate":
        c = replace(c, reviewed_evidence_ids=c.reviewed_evidence_ids * 2)
    elif bad == "foreign":
        c = replace(c, reviewed_evidence_ids=(uuid4(),))
    elif bad == "empty-reason":
        c = replace(c, reason="  ")
    elif bad == "long-reason":
        c = replace(c, reason="x" * 201)
    else:
        key = " "
    before = deepcopy(u.state)
    with pytest.raises(ReviewCommandError):
        await execute(u, c, key)
    assert u.state == before and u.commits == 0


@pytest.mark.parametrize("signal", [False, True])
async def test_successor_keeps_original_links_and_relations_and_resolves_only_explicit_review(
    graph, signal
):
    u = graph
    c = cmd(u)
    if signal:
        c = replace(
            c,
            operation=ReviewOperation.OPEN_CONTRADICTION_REVIEW,
            contradiction_link_ids=(u.state["links"][c.expected_current_version_id][1].id,),
        )
    before = deepcopy(u.state)
    await execute(u, c)
    old = c.expected_current_version_id
    links = before["links"][old]
    c2 = cmd(
        u,
        "NEW_VERSION",
        main_category="Revised",
        content="Explicitly reconsidered",
        evidence=(
            LessonEvidenceInput(links[0].learning_evidence_id, LessonEvidenceRelation.SUPPORTS),
            LessonEvidenceInput(links[1].learning_evidence_id, LessonEvidenceRelation.CONTEXTUAL),
        ),
    )
    result = await execute(u, c2, "version")
    assert result.result_type == "LESSON_VERSION" and u.commits == 2
    assert (
        u.state["lesson"].current_version_id == result.result_id
        and u.state["lesson"].current_state is LessonState.CURRENT
    )
    assert u.state["versions"][old] == before["versions"][old] and u.state["links"][old] == links
    assert u.state["versions"][result.result_id].supersedes_version_id == old
    assert [v.relation for v in u.state["links"][result.result_id]] == [
        LessonEvidenceRelation.SUPPORTS,
        LessonEvidenceRelation.CONTEXTUAL,
    ]
    if signal:
        s = u.state["signals"][c2.expected_open_signal_id]
        assert (
            s.resulting_lesson_version_id == result.result_id
            and s.status is LessonReviewSignalStatus.RESOLVED
        )
    assert (await execute(u, c2, "version")).result_id == result.result_id


@pytest.mark.parametrize("bad", ["blank", "duplicate", "foreign", "no-support"])
async def test_invalid_successor_rolls_back_without_advancing_snapshot(graph, bad):
    u = graph
    await execute(u, cmd(u))
    old = u.state["lesson"].current_version_id
    evid = tuple(
        LessonEvidenceInput(v.learning_evidence_id, v.relation) for v in u.state["links"][old]
    )
    if bad == "duplicate":
        evid = evid + evid[:1]
    elif bad == "foreign":
        evid = (LessonEvidenceInput(uuid4(), LessonEvidenceRelation.SUPPORTS),)
    elif bad == "no-support":
        evid = (replace(evid[0], relation=LessonEvidenceRelation.CONTEXTUAL),)
    c = cmd(
        u,
        "NEW_VERSION",
        main_category="Process",
        content="  " if bad == "blank" else "Explicit new",
        evidence=evid,
    )
    before = deepcopy(u.state)
    with pytest.raises(LessonServiceError):
        await execute(u, c, "version")
    assert u.state == before and u.commits == 1


@pytest.mark.parametrize("link", ["support", "foreign", "duplicate"])
async def test_contradiction_signal_never_uses_stale_supports_as_trigger(graph, link):
    u = graph
    links = u.state["links"][u.state["lesson"].current_version_id]
    ids = (
        (links[0].id,)
        if link == "support"
        else (uuid4(),) if link == "foreign" else (links[1].id,) * 2
    )
    before = deepcopy(u.state)
    with pytest.raises(LessonReviewServiceError):
        await execute(u, cmd(u, "OPEN_CONTRADICTION_REVIEW", contradiction_link_ids=ids))
    assert u.state == before


async def test_commit_failure_rolls_back_entire_command_and_allows_same_retry(graph):
    u = graph
    c = cmd(u)
    before = deepcopy(u.state)
    u.fail_commit = True
    with pytest.raises(RuntimeError, match="commit failure"):
        await execute(u, c)
    assert u.state == before and u.rollbacks == 1 and u.commits == 0
    u.fail_commit = False
    assert not (await execute(u, c)).replayed
    assert u.commits == 1


@pytest.mark.parametrize("with_signal", [False, True])
async def test_retire_is_explicit_and_does_not_remove_history(graph, with_signal):
    u = graph
    c = cmd(u)
    if with_signal:
        c = replace(
            c,
            operation=ReviewOperation.OPEN_CONTRADICTION_REVIEW,
            contradiction_link_ids=(u.state["links"][c.expected_current_version_id][1].id,),
        )
    before = deepcopy(u.state)
    await execute(u, c)
    await execute(u, cmd(u, "RETIRE"), "retire")
    assert u.state["lesson"].current_state is LessonState.RETIRED
    assert u.state["versions"] == before["versions"] and u.state["links"] == before["links"]
    with pytest.raises(ReviewCommandError):
        await execute(u, cmd(u), "cannot-open-retired")
