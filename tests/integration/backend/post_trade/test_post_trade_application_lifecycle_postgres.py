"""Full FT-011 application lifecycle against real PostgreSQL."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from test_post_trade_repositories_postgres import _parents

# Register FK parent tables in shared Base.metadata.
import app.features.market.persistence.models
import app.features.product.persistence.models
import app.features.trade_position.persistence.models  # noqa: F401
from app.features.post_trade.application.exit_review_service import (
    ExitReviewService,
)
from app.features.post_trade.application.handoff_service import (
    Ft012HandoffService,
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
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.unit_of_work import (
    SqlAlchemyPostTradeLearningUnitOfWork,
)

pytestmark = pytest.mark.asyncio

EXIT_AT = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
START_AT = datetime(2026, 8, 18, 13, 0, tzinfo=UTC)
REFRESH_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _trade_context(parents) -> TradeExitContext:
    return TradeExitContext(
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
        product_id=uuid4(),
        is_fully_closed=True,
        full_exit_at=EXIT_AT,
        realized_gross_pnl=Decimal("125.50"),
        executions=(),
        management_events=(),
    )


def _planning_context() -> PlanningContext:
    return PlanningContext(
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        original_stop=Decimal("90"),
        original_targets=(
            Decimal("110"),
            Decimal("120"),
        ),
    )


def _prices(listing_id):
    return tuple(
        DailyObservation(
            listing_id=listing_id,
            trading_date=date(2026, 8, 19) + timedelta(days=i),
            open=Decimal("100"),
            high=Decimal("125"),
            low=Decimal("85"),
            close=Decimal("105"),
            adjusted_close=None,
            quality_status="VALID",
        )
        for i in range(20)
    )


async def test_full_ft011_lifecycle_persists_and_opens_handoff(
    post_trade_session: AsyncSession,
) -> None:
    parents = await _parents(post_trade_session)

    trade = _trade_context(parents)
    planning = _planning_context()
    prices = _prices(parents["listing_id"])

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(return_value=trade)

    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=trade.product_id,
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )
    )

    listing_resolver = MagicMock()
    listing_resolver.resolve = AsyncMock(return_value=parents["listing_id"])

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(return_value=planning)

    market_reader = MagicMock()
    market_reader.list_range = AsyncMock(return_value=prices)

    observation_service = PostTradeObservationService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session),
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=product_reader,
        listing_resolver=listing_resolver,
        market_data_reader=market_reader,
        clock=lambda: START_AT,
        id_factory=uuid4,
    )

    observation = await observation_service.start(
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
        actor_id=parents["actor_id"],
    )

    assert observation.status is PostTradeObservationStatus.ACTIVE
    assert observation.underlying_listing_id == parents["listing_id"]
    assert observation.target_observation_count == 20

    # Refresh uses a later clock so all 20 EOD observations are visible.
    observation_service._clock = lambda: REFRESH_AT

    completed, evidence = await observation_service.refresh(
        workspace_id=parents["workspace_id"],
        observation_id=observation.id,
    )

    assert evidence.available_observation_count == 20
    assert evidence.horizon_complete is True
    assert completed.status is PostTradeObservationStatus.COMPLETED
    assert completed.completed_at is not None

    review_service = ExitReviewService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session),
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        market_data_reader=market_reader,
        clock=lambda: REFRESH_AT,
        id_factory=uuid4,
    )

    review, draft = await review_service.get_or_create_draft(
        workspace_id=parents["workspace_id"],
        observation_id=completed.id,
        actor_id=parents["actor_id"],
    )

    assert draft.status is ExitReviewStatus.DRAFT
    assert draft.version == 1

    updated_draft = await review_service.update_draft(
        workspace_id=parents["workspace_id"],
        review_id=review.id,
        version_id=draft.id,
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale=(
            "Exit war etwas früh, Prozess und Risikoentscheidung " "waren insgesamt belastbar."
        ),
    )

    assert updated_draft.status is ExitReviewStatus.DRAFT
    assert updated_draft.timing is ExitReviewAssessment.IMPROVABLE

    finalized = await review_service.finalize(
        workspace_id=parents["workspace_id"],
        review_id=review.id,
        version_id=updated_draft.id,
        actor_id=parents["actor_id"],
        timing=updated_draft.timing,
        process_adherence=updated_draft.process_adherence,
        risk_decision=updated_draft.risk_decision,
        overall_exit_decision=updated_draft.overall_exit_decision,
        rationale=updated_draft.rationale,
    )

    assert finalized.status is ExitReviewStatus.FINALIZED
    assert finalized.currentness is ExitReviewCurrentness.CURRENT
    assert finalized.input_fingerprint is not None
    assert len(finalized.input_fingerprint) == 64

    handoff = await Ft012HandoffService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session)
    ).get(
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
    )

    assert handoff.ready is True
    assert handoff.reason == "READY"
    assert handoff.post_trade_observation_id == completed.id
    assert handoff.exit_review_id == review.id
    assert handoff.exit_review_version_id == finalized.id


async def test_changed_inputs_turn_finalized_review_stale_and_block_handoff(
    post_trade_session: AsyncSession,
) -> None:
    parents = await _parents(post_trade_session)

    trade = _trade_context(parents)
    planning = _planning_context()
    prices = _prices(parents["listing_id"])

    trade_reader = MagicMock()
    trade_reader.get = AsyncMock(return_value=trade)

    planning_reader = MagicMock()
    planning_reader.get = AsyncMock(return_value=planning)

    product_reader = MagicMock()
    product_reader.get = AsyncMock(
        return_value=ProductContext(
            warrant_id=trade.product_id,
            underlying_id=uuid4(),
            historical_warrant_terms_version_id=None,
            maturity_date=None,
            historical_underlying_listing_id=None,
        )
    )

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=parents["listing_id"])

    market_reader = MagicMock()
    market_reader.list_range = AsyncMock(return_value=prices)

    observation_service = PostTradeObservationService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session),
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=product_reader,
        listing_resolver=resolver,
        market_data_reader=market_reader,
        clock=lambda: START_AT,
    )

    observation = await observation_service.start(
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
        actor_id=parents["actor_id"],
    )

    observation_service._clock = lambda: REFRESH_AT

    completed, _ = await observation_service.refresh(
        workspace_id=parents["workspace_id"],
        observation_id=observation.id,
    )

    review_service = ExitReviewService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session),
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        market_data_reader=market_reader,
        clock=lambda: REFRESH_AT,
    )

    review, draft = await review_service.get_or_create_draft(
        workspace_id=parents["workspace_id"],
        observation_id=completed.id,
        actor_id=parents["actor_id"],
    )

    draft = await review_service.update_draft(
        workspace_id=parents["workspace_id"],
        review_id=review.id,
        version_id=draft.id,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="Original assessment.",
    )

    finalized = await review_service.finalize(
        workspace_id=parents["workspace_id"],
        review_id=review.id,
        version_id=draft.id,
        actor_id=parents["actor_id"],
        timing=draft.timing,
        process_adherence=draft.process_adherence,
        risk_decision=draft.risk_decision,
        overall_exit_decision=draft.overall_exit_decision,
        rationale=draft.rationale,
    )

    assert finalized.currentness is ExitReviewCurrentness.CURRENT

    changed_trade = TradeExitContext(
        workspace_id=trade.workspace_id,
        trade_id=trade.trade_id,
        product_id=trade.product_id,
        is_fully_closed=True,
        full_exit_at=trade.full_exit_at,
        realized_gross_pnl=Decimal("999.99"),
        executions=trade.executions,
        management_events=trade.management_events,
    )
    trade_reader.get = AsyncMock(return_value=changed_trade)

    stale = await review_service.refresh_currentness(
        workspace_id=parents["workspace_id"],
        review_id=review.id,
    )

    assert stale is not None
    assert stale.currentness is ExitReviewCurrentness.STALE
    assert stale.stale_at is not None

    handoff = await Ft012HandoffService(
        uow=SqlAlchemyPostTradeLearningUnitOfWork(post_trade_session)
    ).get(
        workspace_id=parents["workspace_id"],
        trade_id=parents["trade_id"],
    )

    assert handoff.ready is False
    assert handoff.reason == "EXIT_REVIEW_STALE"
