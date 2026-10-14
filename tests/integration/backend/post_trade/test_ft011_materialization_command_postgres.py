"""Real independent-transaction FT-012 handoff tests, not a full trade-capture E2E."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_post_trade_repositories_postgres import NOW, _draft, _review_graph

from app.features.learning.application.ft011_materialization_service import (
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
    MaterializeFt011LearningEvidenceResult,
    MaterializeFt011LearningEvidenceService,
)
from app.features.learning.persistence.ft011_materialization_repository import (
    SqlAlchemyFt011MaterializationRepository,
)
from app.features.learning.persistence.unit_of_work import SqlAlchemyLearningTradeLinkUnitOfWork
from app.features.post_trade.application.handoff_service import Ft012HandoffService
from app.features.post_trade.domain import ExitReviewAssessment
from app.features.post_trade.persistence.unit_of_work import SqlAlchemyPostTradeLearningUnitOfWork


class Clock:
    def now(self):
        return NOW + timedelta(days=32)


class Ids:
    def new_uuid(self):
        return uuid4()


def _finalize(draft, actor):
    return draft.finalize(
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.ACCEPTABLE,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.NOT_ASSESSABLE,
        rationale="Synthetic qualified source for materialization transaction tests.",
        input_fingerprint="a" * 64,
        finalized_at=NOW + timedelta(days=31),
        finalized_by=actor,
    )


@pytest.fixture
async def committed_review(post_trade_test_engine):
    sessions = async_sessionmaker(post_trade_test_engine, expire_on_commit=False)
    async with sessions() as session:
        parents, observation, review, observations, _, versions = await _review_graph(session)
        await observations.replace(observation.complete(completed_at=NOW + timedelta(days=30)))
        draft = _draft(review.id)
        await versions.add(draft)
        await session.flush()
        final = _finalize(draft, parents["actor_id"])
        await versions.replace(final)
        extra = (
            await session.execute(
                text("""
                    SELECT w.id AS warrant_id, w.issuer_id, l.underlying_id,
                           l.trading_venue_id
                    FROM trades t JOIN warrants w ON w.id = t.product_id
                    JOIN listings l ON l.id = :listing_id
                    WHERE t.id = :trade_id
                """),
                parents,
            )
        ).mappings().one()
        owned = {**parents, **extra, "observation_id": observation.id, "review_id": review.id}
        await session.commit()
    try:
        yield sessions, parents, final
    finally:
        # Only this test's UUID graph is removed; no truncation, constraint removal or volumes.
        async with sessions.begin() as session:
            for table, column, key in (
                ("ft012_idempotency_records", "workspace_id", "workspace_id"),
                ("ft011_evidence", "trade_id", "trade_id"),
                ("learning_evidence", "workspace_id", "workspace_id"),
                ("exit_review_versions", "exit_review_id", "review_id"),
                ("exit_reviews", "id", "review_id"),
                ("post_trade_observations", "id", "observation_id"),
                ("trades", "id", "trade_id"),
                ("warrants", "id", "warrant_id"),
                ("listings", "id", "listing_id"),
                ("underlyings", "id", "underlying_id"),
                ("issuers", "id", "issuer_id"),
                ("trading_venues", "id", "trading_venue_id"),
                ("workspaces", "id", "workspace_id"),
            ):
                await session.execute(
                    text(f"DELETE FROM {table} WHERE {column} = :id"), {"id": owned[key]}
                )


class RacingRepository(SqlAlchemyFt011MaterializationRepository):
    def __init__(self, session, barrier):
        super().__init__(session)
        self.barrier = barrier

    async def get_by_source(self, *, workspace_id, exit_review_version_id):
        value = await super().get_by_source(
            workspace_id=workspace_id, exit_review_version_id=exit_review_version_id
        )
        # Both real SELECTs must see absence before either INSERT; no fake persistence.
        assert value is None
        await asyncio.wait_for(self.barrier.wait(), timeout=10)
        return value


def _service(session, barrier=None):
    repository = (
        SqlAlchemyFt011MaterializationRepository(session)
        if barrier is None
        else RacingRepository(session, barrier)
    )
    return MaterializeFt011LearningEvidenceService(
        uow=SqlAlchemyLearningTradeLinkUnitOfWork(session),
        repository=repository,
        handoff_reader=Ft012HandoffService(uow=SqlAlchemyPostTradeLearningUnitOfWork(session)),
        clock=Clock(),
        id_factory=Ids(),
    )


async def _execute(sessions, parents, version_id, key, *, barrier=None, pids=None):
    async with sessions() as session:
        if pids is not None:
            pids.append(await session.scalar(text("SELECT pg_backend_pid()")))
        return await _service(session, barrier).execute(
            workspace_id=parents["workspace_id"],
            trade_id=parents["trade_id"],
            idempotency_key=key,
            expected_exit_review_version_id=version_id,
        )


async def _count(sessions, parents):
    async with sessions() as session:
        return await session.scalar(
            text("SELECT count(*) FROM learning_evidence WHERE workspace_id = :workspace_id"),
            parents,
        )


@pytest.mark.parametrize("same_key", [True, False])
async def test_parallel_handoffs_have_one_source_and_retry_recovers(committed_review, same_key):
    sessions, parents, final = committed_review
    keys = ["race-a", "race-a" if same_key else "race-b"]
    barrier = asyncio.Barrier(2)
    pids = []
    results = await asyncio.wait_for(
        asyncio.gather(
            *(
                _execute(sessions, parents, final.id, key, barrier=barrier, pids=pids)
                for key in keys
            ),
            return_exceptions=True,
        ),
        timeout=20,
    )
    assert len(set(pids)) == 2  # Independently committed/rolled-back PostgreSQL connections.
    successes = [r for r in results if isinstance(r, MaterializeFt011LearningEvidenceResult)]
    errors = [r for r in results if isinstance(r, Ft011MaterializationError)]
    assert len(successes) == len(errors) == 1, results
    assert errors[0].code is Ft011MaterializationErrorCode.MATERIALIZATION_CONFLICT
    for key in keys:
        retried = await _execute(sessions, parents, final.id, key)
        assert retried.learning_evidence_id == successes[0].learning_evidence_id
        assert retried.exit_review_version_id == final.id
        assert retried.created is False
    assert await _count(sessions, parents) == 1  # Losing transaction left no orphan parent.
    async with sessions() as session:
        assert await session.scalar(
            text("SELECT count(*) FROM ft011_evidence WHERE exit_review_version_id = :id"),
            {"id": final.id},
        ) == 1
        assert await session.scalar(
            text("SELECT count(*) FROM ft012_idempotency_records WHERE workspace_id = :workspace_id"),
            parents,
        ) == (1 if same_key else 2)


async def test_wrong_version_stale_replay_and_successor_keep_exact_provenance(committed_review):
    sessions, parents, final = committed_review
    with pytest.raises(Ft011MaterializationError) as mismatch:
        await _execute(sessions, parents, uuid4(), "wrong")
    assert mismatch.value.code is Ft011MaterializationErrorCode.SOURCE_VERSION_MISMATCH
    assert await _count(sessions, parents) == 0
    original = await _execute(sessions, parents, final.id, "original")
    async with sessions() as session:
        uow = SqlAlchemyPostTradeLearningUnitOfWork(session)
        await uow.exit_review_versions.replace(
            final.mark_stale(stale_at=NOW + timedelta(days=32), stale_reason="INPUT_CHANGED")
        )
        await session.commit()
    with pytest.raises(Ft011MaterializationError) as stale:
        await _execute(sessions, parents, final.id, "new-after-stale")
    assert stale.value.code is Ft011MaterializationErrorCode.SOURCE_NOT_READY
    replay = await _execute(sessions, parents, final.id, "original")
    assert replay.replayed and replay.learning_evidence_id == original.learning_evidence_id
    async with sessions() as session:
        uow = SqlAlchemyPostTradeLearningUnitOfWork(session)
        successor = _draft(final.exit_review_id, version=2, supersedes=final.id)
        await uow.exit_review_versions.add(successor)
        await session.flush()
        await uow.exit_review_versions.replace(_finalize(successor, parents["actor_id"]))
        await session.commit()
    with pytest.raises(Ft011MaterializationError) as old_pin:
        await _execute(sessions, parents, final.id, "old-view")
    assert old_pin.value.code is Ft011MaterializationErrorCode.SOURCE_VERSION_MISMATCH
    new = await _execute(sessions, parents, successor.id, "successor")
    assert new.created and new.learning_evidence_id != original.learning_evidence_id
    assert await _count(sessions, parents) == 2
    async with sessions() as session:
        source = await SqlAlchemyFt011MaterializationRepository(session).get_by_evidence_id(
            workspace_id=parents["workspace_id"], evidence_id=original.learning_evidence_id
        )
        assert source is not None
        assert source.source.exit_review_version_id == final.id
        assert source.source.trade_id == parents["trade_id"]
