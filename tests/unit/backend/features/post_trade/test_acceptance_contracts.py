"""Explicit acceptance-contract tests for FT-011 Sprint 11 gaps."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.features.post_trade.api.dependencies import (
    get_exit_review_service,
    get_post_trade_query_service,
)
from app.features.post_trade.application.exit_review_service import (
    ExitReviewService,
)
from app.features.post_trade.application.observation_service import (
    PostTradeObservationService,
)
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    ProductContext,
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
from app.main import create_application

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _uow():
    uow = MagicMock()

    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.flush = AsyncMock()

    uow.observations = MagicMock()
    uow.exit_reviews = MagicMock()
    uow.exit_review_versions = MagicMock()

    return uow


def _trade(
    *,
    workspace_id,
    trade_id,
) -> TradeExitContext:
    return TradeExitContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        product_id=uuid4(),
        is_fully_closed=True,
        full_exit_at=NOW,
        realized_gross_pnl=Decimal("10"),
        executions=(),
        management_events=(),
    )


def _observation(
    *,
    workspace_id,
    trade_id,
) -> PostTradeObservation:
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=workspace_id,
        trade_id=trade_id,
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.COMPLETED,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=NOW + timedelta(days=30),
        created_at=NOW,
        updated_at=NOW + timedelta(days=30),
    )


@pytest.mark.asyncio
async def test_at_s11_016_maturity_does_not_stop_underlying_horizon() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    listing_id = uuid4()

    observation = PostTradeObservation(
        id=uuid4(),
        workspace_id=workspace_id,
        trade_id=trade_id,
        underlying_listing_id=listing_id,
        status=PostTradeObservationStatus.ACTIVE,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )

    uow = _uow()
    uow.observations.get = AsyncMock(return_value=observation)
    uow.observations.replace = AsyncMock()

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(
        return_value=PlanningContext(
            trade_plan_id=None,
            trade_plan_version_id=None,
            original_stop=None,
            original_targets=(),
        )
    )

    # Maturity occurs after observation point 7.
    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=uuid4(),
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=uuid4(),
            maturity_date=date(2026, 8, 27),
            historical_underlying_listing_id=listing_id,
        )
    )

    prices = tuple(
        DailyObservation(
            listing_id=listing_id,
            trading_date=date(2026, 8, 19) + timedelta(days=i),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            adjusted_close=None,
            quality_status="VALID",
        )
        for i in range(20)
    )

    market_reader = MagicMock()
    market_reader.list_range = AsyncMock(return_value=prices)

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=product_reader,
        listing_resolver=MagicMock(),
        market_data_reader=market_reader,
        clock=lambda: NOW + timedelta(days=40),
    )

    completed, evidence = await service.refresh(
        workspace_id=workspace_id,
        observation_id=observation.id,
    )

    assert evidence.available_observation_count == 20
    assert evidence.horizon_complete is True
    assert completed.status is PostTradeObservationStatus.COMPLETED

    # The evidence is Underlying-EOD evidence; maturity did not truncate it.
    assert len(evidence.points) == 20
    assert evidence.points[-1].trading_date > date(2026, 8, 27)


def test_at_s11_022_and_032_not_assessable_is_valid_final_assessment() -> None:
    review_id = uuid4()
    actor_id = uuid4()

    draft = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review_id,
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
        created_by=actor_id,
    )

    finalized = draft.finalize(
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.NOT_ASSESSABLE,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.IMPROVABLE,
        rationale="Plan context unavailable; process adherence not assessable.",
        input_fingerprint="a" * 64,
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=actor_id,
    )

    assert finalized.status is ExitReviewStatus.FINALIZED
    assert finalized.process_adherence is ExitReviewAssessment.NOT_ASSESSABLE


@pytest.mark.asyncio
async def test_at_s11_030_external_trade_without_plan_can_start_observation() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    listing_id = uuid4()

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=None)
    uow.observations.add = AsyncMock()

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(
        return_value=_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
    )

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(
        return_value=PlanningContext(
            trade_plan_id=None,
            trade_plan_version_id=None,
            original_stop=None,
            original_targets=(),
        )
    )

    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=uuid4(),
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )
    )

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=listing_id)

    service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=product_reader,
        listing_resolver=resolver,
        market_data_reader=MagicMock(),
        clock=lambda: NOW + timedelta(minutes=1),
    )

    result = await service.start(
        workspace_id=workspace_id,
        trade_id=trade_id,
        actor_id=uuid4(),
    )

    assert result.status is PostTradeObservationStatus.ACTIVE
    assert result.target_observation_count == 20
    assert result.underlying_listing_id == listing_id
    uow.observations.add.assert_awaited_once()


def test_at_s11_021_empty_rationale_returns_stable_error_code() -> None:
    app = create_application()

    trade_id = uuid4()
    workspace_id = UUID_WORKSPACE

    observation = _observation(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )

    review = MagicMock()
    review.id = uuid4()

    draft = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.DRAFT,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="   ",
        input_fingerprint=None,
        created_at=NOW,
        created_by=uuid4(),
    )

    query = MagicMock()
    query.get_open_draft = AsyncMock(
        return_value=MagicMock(
            observation=observation,
            review=review,
            version=draft,
        )
    )

    service = MagicMock(spec=ExitReviewService)

    app.dependency_overrides[get_post_trade_query_service] = lambda: query
    app.dependency_overrides[get_exit_review_service] = lambda: service

    try:
        response = TestClient(app).post(
            f"/api/v1/post-trade/trades/{trade_id}/exit-review/finalize"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["code"] == "EXIT_REVIEW_RATIONALE_REQUIRED"
    service.finalize.assert_not_called()


# Must match the current local workspace contract used by the router.
UUID_WORKSPACE = __import__("uuid").UUID("00000000-0000-4000-8000-000000000001")
