"""Unit tests for FT-011 ExitReview application lifecycle."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.exit_review_service import (
    ExitReviewAlreadyFinalizedError,
    ExitReviewObservationIncompleteError,
    ExitReviewService,
)
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    TradeExitContext,
)
from app.features.post_trade.domain import (
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    uow.flush = AsyncMock()
    uow.commit = AsyncMock()

    uow.observations = MagicMock()
    uow.exit_reviews = MagicMock()
    uow.exit_review_versions = MagicMock()

    uow.observations.get = AsyncMock()

    uow.exit_reviews.get = AsyncMock()
    uow.exit_reviews.get_for_observation = AsyncMock()
    uow.exit_reviews.add = AsyncMock()

    uow.exit_review_versions.get = AsyncMock()
    uow.exit_review_versions.get_open_draft = AsyncMock()
    uow.exit_review_versions.next_version_number = AsyncMock(return_value=1)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=None)
    uow.exit_review_versions.get_current_finalized = AsyncMock()
    uow.exit_review_versions.add = AsyncMock()
    uow.exit_review_versions.replace = AsyncMock()

    return uow


def _observation(
    *,
    workspace_id,
    trade_id,
    completed=True,
):
    completed_at = NOW + timedelta(days=30) if completed else None

    return PostTradeObservation(
        id=uuid4(),
        workspace_id=workspace_id,
        trade_id=trade_id,
        underlying_listing_id=uuid4(),
        status=(
            PostTradeObservationStatus.COMPLETED if completed else PostTradeObservationStatus.ACTIVE
        ),
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=completed_at,
        created_at=NOW,
        updated_at=completed_at or NOW,
    )


def _trade(
    *,
    workspace_id,
    trade_id,
    pnl="100",
):
    return TradeExitContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        product_id=uuid4(),
        is_fully_closed=True,
        full_exit_at=NOW,
        realized_gross_pnl=Decimal(pnl),
        executions=(),
        management_events=(),
    )


def _planning():
    return PlanningContext(
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        original_stop=Decimal("90"),
        original_targets=(Decimal("110"),),
    )


def _prices(listing_id):
    return tuple(
        DailyObservation(
            listing_id=listing_id,
            trading_date=date(2026, 8, 19) + timedelta(days=i),
            open=Decimal("100"),
            high=Decimal("115"),
            low=Decimal("85"),
            close=Decimal("105"),
            adjusted_close=None,
            quality_status="VALID",
        )
        for i in range(20)
    )


def _service(
    *,
    uow,
    trade,
    planning,
    prices,
    clock=lambda: NOW + timedelta(days=40),
):
    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(return_value=trade)

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(return_value=planning)

    market_reader = MagicMock()
    market_reader.list_range = AsyncMock(return_value=prices)

    return ExitReviewService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        market_data_reader=market_reader,
        clock=clock,
        id_factory=uuid4,
    )


@pytest.mark.asyncio
async def test_draft_requires_completed_observation() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()

    uow = _uow()
    uow.observations.get = AsyncMock(
        return_value=_observation(
            workspace_id=workspace_id,
            trade_id=trade_id,
            completed=False,
        )
    )

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        ),
        planning=_planning(),
        prices=(),
    )

    with pytest.raises(
        ExitReviewObservationIncompleteError,
        match="not completed",
    ):
        await service.get_or_create_draft(
            workspace_id=workspace_id,
            observation_id=uuid4(),
            actor_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_get_or_create_draft_creates_review_and_version() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=None)
    uow.exit_review_versions.get_open_draft = AsyncMock(return_value=None)
    uow.exit_review_versions.next_version_number = AsyncMock(return_value=1)

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        ),
        planning=_planning(),
        prices=_prices(observation.underlying_listing_id),
    )

    review, draft = await service.get_or_create_draft(
        workspace_id=workspace_id,
        observation_id=observation.id,
        actor_id=uuid4(),
    )

    assert review.post_trade_observation_id == observation.id
    assert draft.exit_review_id == review.id
    assert draft.version == 1
    assert draft.status is ExitReviewStatus.DRAFT
    assert draft.currentness is ExitReviewCurrentness.CURRENT

    uow.exit_reviews.add.assert_awaited_once_with(review)
    uow.flush.assert_awaited_once()
    uow.exit_review_versions.add.assert_awaited_once_with(draft)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_open_draft_is_reused() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()

    existing = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
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
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_open_draft = AsyncMock(return_value=existing)

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        ),
        planning=_planning(),
        prices=_prices(observation.underlying_listing_id),
    )

    returned_review, returned_draft = await service.get_or_create_draft(
        workspace_id=workspace_id,
        observation_id=observation.id,
        actor_id=uuid4(),
    )

    assert returned_review is review
    assert returned_draft is existing

    uow.exit_review_versions.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_draft_supersedes_latest_version() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()

    latest = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.STALE,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="previous review",
        input_fingerprint="a" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
        stale_at=NOW + timedelta(minutes=2),
        stale_reason="changed",
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_open_draft = AsyncMock(return_value=None)
    uow.exit_review_versions.next_version_number = AsyncMock(return_value=2)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=latest)

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        ),
        planning=_planning(),
        prices=_prices(observation.underlying_listing_id),
    )

    _, draft = await service.get_or_create_draft(
        workspace_id=workspace_id,
        observation_id=observation.id,
        actor_id=uuid4(),
    )

    assert draft.version == 2
    assert draft.supersedes_version_id == latest.id


@pytest.mark.asyncio
async def test_finalize_sets_assessments_and_fingerprint() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()
    review.post_trade_observation_id = observation.id

    draft = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
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
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get = AsyncMock(return_value=draft)
    uow.observations.get = AsyncMock(return_value=observation)

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        ),
        planning=_planning(),
        prices=_prices(observation.underlying_listing_id),
    )

    result = await service.finalize(
        workspace_id=workspace_id,
        review_id=review.id,
        version_id=draft.id,
        actor_id=uuid4(),
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="Timing zu früh, Prozess sauber.",
    )

    assert result.status is ExitReviewStatus.FINALIZED
    assert result.currentness is ExitReviewCurrentness.CURRENT
    assert result.timing is ExitReviewAssessment.IMPROVABLE
    assert result.input_fingerprint is not None
    assert len(result.input_fingerprint) == 64

    uow.exit_review_versions.replace.assert_awaited_once_with(result)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_rejects_already_finalized_version() -> None:
    workspace_id = uuid4()
    review = MagicMock()
    review.id = uuid4()

    version = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="done",
        input_fingerprint="a" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get = AsyncMock(return_value=version)

    service = _service(
        uow=uow,
        trade=MagicMock(),
        planning=MagicMock(),
        prices=(),
    )

    with pytest.raises(ExitReviewAlreadyFinalizedError):
        await service.finalize(
            workspace_id=workspace_id,
            review_id=review.id,
            version_id=version.id,
            actor_id=uuid4(),
            timing=ExitReviewAssessment.GOOD,
            process_adherence=ExitReviewAssessment.GOOD,
            risk_decision=ExitReviewAssessment.GOOD,
            overall_exit_decision=ExitReviewAssessment.GOOD,
            rationale="again",
        )


@pytest.mark.asyncio
async def test_identical_inputs_remain_current() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()
    review.post_trade_observation_id = observation.id

    trade = _trade(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )
    planning = _planning()
    prices = _prices(observation.underlying_listing_id)

    from app.features.post_trade.application.input_fingerprint import (
        build_exit_review_input_fingerprint,
    )
    from app.features.post_trade.domain.observation_metrics import (
        build_observation_evidence,
    )

    evidence = build_observation_evidence(
        prices,
        full_exit_at=trade.full_exit_at,
        target_count=20,
        targets=planning.original_targets,
        stop=planning.original_stop,
    )

    fingerprint = build_exit_review_input_fingerprint(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )

    current = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="done",
        input_fingerprint=fingerprint,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get_current_finalized = AsyncMock(return_value=current)
    uow.observations.get = AsyncMock(return_value=observation)

    service = _service(
        uow=uow,
        trade=trade,
        planning=planning,
        prices=prices,
    )

    result = await service.refresh_currentness(
        workspace_id=workspace_id,
        review_id=review.id,
    )

    assert result is current
    assert result.currentness is ExitReviewCurrentness.CURRENT
    uow.exit_review_versions.replace.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_changed_input_marks_review_stale() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()
    review.post_trade_observation_id = observation.id

    current = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="done",
        input_fingerprint="0" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get_current_finalized = AsyncMock(return_value=current)
    uow.observations.get = AsyncMock(return_value=observation)

    service = _service(
        uow=uow,
        trade=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
            pnl="999",
        ),
        planning=_planning(),
        prices=_prices(observation.underlying_listing_id),
    )

    result = await service.refresh_currentness(
        workspace_id=workspace_id,
        review_id=review.id,
    )

    assert result is not None
    assert result.currentness is ExitReviewCurrentness.STALE
    assert result.stale_at is not None
    assert result.stale_reason is not None

    uow.exit_review_versions.replace.assert_awaited_once_with(result)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_draft_persists_assessments_without_finalizing() -> None:
    workspace_id = uuid4()

    review = MagicMock()
    review.id = uuid4()

    draft = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
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
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get = AsyncMock(return_value=draft)

    service = _service(
        uow=uow,
        trade=MagicMock(),
        planning=MagicMock(),
        prices=(),
    )

    updated = await service.update_draft(
        workspace_id=workspace_id,
        review_id=review.id,
        version_id=draft.id,
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="Timing verbessern, Prozess beibehalten.",
    )

    assert updated.id == draft.id
    assert updated.version == draft.version
    assert updated.status is ExitReviewStatus.DRAFT
    assert updated.currentness is ExitReviewCurrentness.CURRENT

    assert updated.timing is ExitReviewAssessment.IMPROVABLE
    assert updated.process_adherence is ExitReviewAssessment.GOOD
    assert updated.risk_decision is ExitReviewAssessment.ACCEPTABLE
    assert updated.overall_exit_decision is ExitReviewAssessment.ACCEPTABLE

    assert updated.rationale == ("Timing verbessern, Prozess beibehalten.")

    assert updated.input_fingerprint is None
    assert updated.finalized_at is None
    assert updated.finalized_by is None

    uow.exit_review_versions.replace.assert_awaited_once_with(updated)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_draft_rejects_finalized_version() -> None:
    workspace_id = uuid4()

    review = MagicMock()
    review.id = uuid4()

    finalized = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="final",
        input_fingerprint="a" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
    )

    uow = _uow()
    uow.exit_reviews.get = AsyncMock(return_value=review)
    uow.exit_review_versions.get = AsyncMock(return_value=finalized)

    service = _service(
        uow=uow,
        trade=MagicMock(),
        planning=MagicMock(),
        prices=(),
    )

    with pytest.raises(
        ExitReviewAlreadyFinalizedError,
        match="not editable",
    ):
        await service.update_draft(
            workspace_id=workspace_id,
            review_id=review.id,
            version_id=finalized.id,
            timing=ExitReviewAssessment.GOOD,
            process_adherence=ExitReviewAssessment.GOOD,
            risk_decision=ExitReviewAssessment.GOOD,
            overall_exit_decision=ExitReviewAssessment.GOOD,
            rationale="cannot edit",
        )

    uow.exit_review_versions.replace.assert_not_awaited()
    uow.commit.assert_not_awaited()
