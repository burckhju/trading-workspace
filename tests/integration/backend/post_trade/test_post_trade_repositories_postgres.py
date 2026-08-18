"""Real PostgreSQL integration tests for FT-011 persistence."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Register all FK parent tables in shared Base.metadata.
# Required by SQLAlchemy mapper dependency sorting during flush.
import app.features.market.persistence.models
import app.features.product.persistence.models
import app.features.trade_position.persistence.models  # noqa: F401
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.repositories import (
    SqlAlchemyExitReviewRepository,
    SqlAlchemyExitReviewVersionRepository,
    SqlAlchemyPostTradeObservationRepository,
)
from app.features.post_trade.persistence.unit_of_work import (
    SqlAlchemyPostTradeLearningUnitOfWork,
)

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


async def _parents(session: AsyncSession):
    workspace_id = uuid4()
    venue_id = uuid4()
    underlying_id = uuid4()
    listing_id = uuid4()
    issuer_id = uuid4()
    warrant_id = uuid4()
    trade_id = uuid4()
    actor_id = uuid4()

    await session.execute(
        text("""
            INSERT INTO workspaces (
                id, name, created_at
            ) VALUES (
                :id, :name, :created_at
            )
            """),
        {
            "id": workspace_id,
            "name": f"S11-{workspace_id}",
            "created_at": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO trading_venues (
                id, mic, name, country_code, timezone,
                is_active, reference_version, version,
                created_at, updated_at
            ) VALUES (
                :id, :mic, :name, 'DE', 'Europe/Berlin',
                true, 'S11-TEST', 1,
                :now, :now
            )
            """),
        {
            "id": venue_id,
            "mic": "X" + uuid4().hex[:3].upper(),
            "name": "S11 Test Venue",
            "now": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO currencies (
                code, name, minor_unit, is_active,
                reference_version, created_at, updated_at
            ) VALUES (
                :code, 'S11 Test Currency', 2, true,
                'S11-TEST', :now, :now
            )
            ON CONFLICT (code) DO NOTHING
            """),
        {
            "code": "EUR",
            "now": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO issuers (
                id, legal_name, display_name, country_code,
                lei, is_active, version, created_at, updated_at
            ) VALUES (
                :id, :legal_name, :display_name, 'DE',
                NULL, true, 1, :now, :now
            )
            """),
        {
            "id": issuer_id,
            "legal_name": f"S11 Issuer {issuer_id}",
            "display_name": "S11 Issuer",
            "now": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO underlyings (
                id, workspace_id, type, name, isin, wkn,
                lifecycle_status, quality_status, version,
                created_at, updated_at, data_origin
            ) VALUES (
                :id, :workspace_id, 'STOCK', :name,
                NULL, NULL,
                'ACTIVE', 'COMPLETE', 1,
                :now, :now, 'MANUAL'
            )
            """),
        {
            "id": underlying_id,
            "workspace_id": workspace_id,
            "name": f"S11 Underlying {underlying_id}",
            "now": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO listings (
                id, workspace_id, underlying_id,
                trading_venue_id, ticker, currency_code,
                lifecycle_status, is_primary, version,
                created_at, updated_at, data_origin
            ) VALUES (
                :id, :workspace_id, :underlying_id,
                :venue_id, :ticker, 'EUR',
                'ACTIVE', true, 1,
                :now, :now, 'MANUAL'
            )
            """),
        {
            "id": listing_id,
            "workspace_id": workspace_id,
            "underlying_id": underlying_id,
            "venue_id": venue_id,
            "ticker": "S" + uuid4().hex[:8].upper(),
            "now": NOW,
        },
    )

    # ProductFamily/WarrantLifecycle are persisted as strings.
    # Use the actual enum values from the domain at runtime.
    from app.features.product.domain.models import (
        ProductFamily,
        WarrantLifecycle,
    )

    product_family = next(iter(ProductFamily)).value
    lifecycle = next(iter(WarrantLifecycle)).value

    await session.execute(
        text("""
            INSERT INTO warrants (
                id, workspace_id, issuer_id, underlying_id,
                product_family, display_name, isin, wkn,
                lifecycle_status, version,
                created_at, updated_at
            ) VALUES (
                :id, :workspace_id, :issuer_id, :underlying_id,
                :product_family, :display_name, NULL, NULL,
                :lifecycle, 1,
                :now, :now
            )
            """),
        {
            "id": warrant_id,
            "workspace_id": workspace_id,
            "issuer_id": issuer_id,
            "underlying_id": underlying_id,
            "product_family": product_family,
            "display_name": "S11 Test Warrant",
            "lifecycle": lifecycle,
            "now": NOW,
        },
    )

    await session.execute(
        text("""
            INSERT INTO trades (
                id, workspace_id, product_id, origin,
                created_at, created_by,
                trade_plan_id, trade_plan_version_id,
                product_selection_id, product_evaluation_id
            ) VALUES (
                :id, :workspace_id, :product_id, 'EXTERNAL',
                :created_at, :created_by,
                NULL, NULL, NULL, NULL
            )
            """),
        {
            "id": trade_id,
            "workspace_id": workspace_id,
            "product_id": warrant_id,
            "created_at": NOW,
            "created_by": actor_id,
        },
    )

    await session.flush()

    return {
        "workspace_id": workspace_id,
        "listing_id": listing_id,
        "trade_id": trade_id,
        "actor_id": actor_id,
    }


def _observation(parents):
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
        underlying_listing_id=parents["listing_id"],
        status=PostTradeObservationStatus.ACTIVE,
        target_observation_count=20,
        started_at=NOW,
        started_by=parents["actor_id"],
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _draft(review_id, *, version=1, supersedes=None):
    return ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review_id,
        version=version,
        status=ExitReviewStatus.DRAFT,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=None,
        process_adherence=None,
        risk_decision=None,
        overall_exit_decision=None,
        rationale=None,
        input_fingerprint=None,
        created_at=NOW,
        created_by=uuid4(),
        supersedes_version_id=supersedes,
    )


async def _review_graph(session: AsyncSession):
    parents = await _parents(session)

    observations = SqlAlchemyPostTradeObservationRepository(session)
    reviews = SqlAlchemyExitReviewRepository(session)
    versions = SqlAlchemyExitReviewVersionRepository(
        session,
        reviews,
    )

    observation = _observation(parents)
    await observations.add(observation)
    await session.flush()

    review = ExitReview(
        id=uuid4(),
        workspace_id=parents["workspace_id"],
        post_trade_observation_id=observation.id,
        created_at=NOW,
        created_by=parents["actor_id"],
    )
    await reviews.add(review)
    await session.flush()

    return parents, observation, review, observations, reviews, versions


async def test_observation_repository_round_trip_and_replace(
    post_trade_session: AsyncSession,
) -> None:
    parents = await _parents(post_trade_session)
    repository = SqlAlchemyPostTradeObservationRepository(post_trade_session)

    observation = _observation(parents)

    await repository.add(observation)
    await post_trade_session.flush()

    by_id = await repository.get(
        parents["workspace_id"],
        observation.id,
    )
    by_trade = await repository.get_for_trade(
        parents["workspace_id"],
        parents["trade_id"],
    )

    assert by_id == observation
    assert by_trade == observation

    completed_at = NOW + timedelta(days=30)
    completed = observation.complete(completed_at=completed_at)

    await repository.replace(completed)
    await post_trade_session.flush()

    loaded = await repository.get(
        parents["workspace_id"],
        observation.id,
    )

    assert loaded is not None
    assert loaded.status is PostTradeObservationStatus.COMPLETED
    assert loaded.completed_at == completed_at


async def test_database_rejects_second_observation_for_same_trade(
    post_trade_session: AsyncSession,
) -> None:
    parents = await _parents(post_trade_session)
    repository = SqlAlchemyPostTradeObservationRepository(post_trade_session)

    await repository.add(_observation(parents))
    await post_trade_session.flush()

    await repository.add(_observation(parents))

    with pytest.raises(IntegrityError):
        await post_trade_session.flush()


async def test_review_and_version_repository_round_trip(
    post_trade_session: AsyncSession,
) -> None:
    (
        parents,
        observation,
        review,
        _,
        reviews,
        versions,
    ) = await _review_graph(post_trade_session)

    loaded_review = await reviews.get(
        parents["workspace_id"],
        review.id,
    )
    by_observation = await reviews.get_for_observation(
        parents["workspace_id"],
        observation.id,
    )

    assert loaded_review == review
    assert by_observation == review

    draft = _draft(review.id)

    await versions.add(draft)
    await post_trade_session.flush()

    assert await versions.get(draft.id) == draft
    assert await versions.get_latest(review.id) == draft
    assert await versions.get_open_draft(review.id) == draft
    assert (
        await versions.next_version_number(
            parents["workspace_id"],
            review.id,
        )
        == 2
    )


async def test_database_rejects_second_open_draft(
    post_trade_session: AsyncSession,
) -> None:
    (
        _,
        _,
        review,
        _,
        _,
        versions,
    ) = await _review_graph(post_trade_session)

    await versions.add(_draft(review.id, version=1))
    await post_trade_session.flush()

    await versions.add(_draft(review.id, version=2))

    with pytest.raises(IntegrityError):
        await post_trade_session.flush()


async def test_finalized_current_version_is_queryable(
    post_trade_session: AsyncSession,
) -> None:
    (
        parents,
        _,
        review,
        _,
        _,
        versions,
    ) = await _review_graph(post_trade_session)

    draft = _draft(review.id)
    await versions.add(draft)
    await post_trade_session.flush()

    finalized = draft.finalize(
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.ACCEPTABLE,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.IMPROVABLE,
        rationale="PostgreSQL integration review.",
        input_fingerprint="a" * 64,
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=parents["actor_id"],
    )

    await versions.replace(finalized)
    await post_trade_session.flush()

    current = await versions.get_current_finalized(review.id)

    assert current is not None
    assert current.id == finalized.id
    assert current.status is ExitReviewStatus.FINALIZED
    assert current.currentness is ExitReviewCurrentness.CURRENT
    assert await versions.get_open_draft(review.id) is None


async def test_uow_commit_is_visible_inside_test_but_outer_fixture_rolls_back(
    post_trade_session: AsyncSession,
) -> None:
    parents = await _parents(post_trade_session)
    observation = _observation(parents)

    uow = SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session)

    async with uow:
        await uow.observations.add(observation)
        await uow.commit()

    loaded = await uow.observations.get(
        parents["workspace_id"],
        observation.id,
    )

    assert loaded == observation
