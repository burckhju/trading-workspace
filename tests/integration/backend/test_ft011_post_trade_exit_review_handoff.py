from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.exit_review_service import ExitReviewService
from app.features.post_trade.application.handoff_service import Ft012HandoffService
from app.features.post_trade.application.observation_service import PostTradeObservationService
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    ProductContext,
    TradeExitContext,
)
from app.features.post_trade.domain import (
    ExitReviewAssessment,
    ExitReviewStatus,
    PostTradeObservationStatus,
)

EXIT_AT = datetime(2026, 8, 27, 10, 0, tzinfo=UTC)
REVIEW_AT = EXIT_AT + timedelta(days=30)


class MemoryUow:
    def __init__(self) -> None:
        self.observation = None
        self.review = None
        self.versions = []
        self.observations = SimpleNamespace(
            get_for_trade=self._get_observation_for_trade,
            get=self._get_observation,
            add=self._add_observation,
            replace=self._replace_observation,
        )
        self.exit_reviews = SimpleNamespace(
            get_for_observation=self._get_review_for_observation,
            get=self._get_review,
            add=self._add_review,
        )
        self.exit_review_versions = SimpleNamespace(
            get_open_draft=self._get_open_draft,
            next_version_number=self._next_version_number,
            get_latest=self._get_latest,
            get=self._get_version,
            add=self._add_version,
            replace=self._replace_version,
        )
        self.commit = AsyncMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def _get_observation_for_trade(self, workspace_id, trade_id):
        if self.observation is None:
            return None
        if self.observation.workspace_id == workspace_id and self.observation.trade_id == trade_id:
            return self.observation
        return None

    async def _get_observation(self, workspace_id, observation_id):
        if (
            self.observation is not None
            and self.observation.workspace_id == workspace_id
            and self.observation.id == observation_id
        ):
            return self.observation
        return None

    async def _add_observation(self, observation):
        self.observation = observation

    async def _replace_observation(self, observation):
        self.observation = observation

    async def _get_review_for_observation(self, workspace_id, observation_id):
        if (
            self.review is not None
            and self.review.workspace_id == workspace_id
            and self.review.post_trade_observation_id == observation_id
        ):
            return self.review
        return None

    async def _get_review(self, workspace_id, review_id):
        if (
            self.review is not None
            and self.review.workspace_id == workspace_id
            and self.review.id == review_id
        ):
            return self.review
        return None

    async def _add_review(self, review):
        self.review = review

    async def _get_open_draft(self, review_id):
        return next(
            (
                version
                for version in self.versions
                if version.exit_review_id == review_id and version.status is ExitReviewStatus.DRAFT
            ),
            None,
        )

    async def _next_version_number(self, workspace_id, review_id):
        return 1 + max(
            (version.version for version in self.versions if version.exit_review_id == review_id),
            default=0,
        )

    async def _get_latest(self, review_id):
        matches = [v for v in self.versions if v.exit_review_id == review_id]
        return max(matches, key=lambda item: item.version) if matches else None

    async def _get_version(self, version_id):
        return next((v for v in self.versions if v.id == version_id), None)

    async def _add_version(self, version):
        self.versions.append(version)

    async def _replace_version(self, version):
        self.versions = [version if item.id == version.id else item for item in self.versions]


@pytest.mark.asyncio
async def test_closed_workspace_trade_reaches_finalized_current_ft011_review() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    product_id = uuid4()
    actor_id = uuid4()
    listing_id = uuid4()
    trade_plan_id = uuid4()
    trade_plan_version_id = uuid4()

    trade = TradeExitContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        product_id=product_id,
        is_fully_closed=True,
        full_exit_at=EXIT_AT,
        realized_gross_pnl=Decimal("125.00"),
        executions=(),
        management_events=(),
    )
    planning = PlanningContext(
        trade_plan_id=trade_plan_id,
        trade_plan_version_id=trade_plan_version_id,
        original_stop=Decimal("95"),
        original_targets=(Decimal("110"), Decimal("120")),
    )
    product = ProductContext(
        warrant_id=product_id,
        underlying_id=uuid4(),
        historical_warrant_terms_version_id=uuid4(),
        maturity_date=None,
        historical_underlying_listing_id=listing_id,
    )
    prices = tuple(
        DailyObservation(
            listing_id=listing_id,
            trading_date=date(2026, 8, 28) + timedelta(days=index),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
            adjusted_close=None,
            quality_status="VALID",
        )
        for index in range(20)
    )

    uow = MemoryUow()
    trade_reader = SimpleNamespace(get=AsyncMock(return_value=trade))
    planning_reader = SimpleNamespace(get=AsyncMock(return_value=planning))
    product_reader = SimpleNamespace(get=AsyncMock(return_value=product))
    listing_resolver = SimpleNamespace(resolve=AsyncMock(return_value=listing_id))
    market_reader = SimpleNamespace(list_range=AsyncMock(return_value=prices))

    observation_service = PostTradeObservationService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        product_reader=product_reader,
        listing_resolver=listing_resolver,
        market_data_reader=market_reader,
        clock=lambda: EXIT_AT + timedelta(minutes=1),
    )
    observation = await observation_service.start(
        workspace_id=workspace_id,
        trade_id=trade_id,
        actor_id=actor_id,
    )
    assert observation.status is PostTradeObservationStatus.ACTIVE
    assert observation.trade_id == trade_id
    assert observation.underlying_listing_id == listing_id

    observation_service._clock = lambda: REVIEW_AT
    completed, evidence = await observation_service.refresh(
        workspace_id=workspace_id,
        observation_id=observation.id,
    )
    assert completed.status is PostTradeObservationStatus.COMPLETED
    assert evidence.horizon_complete is True
    assert evidence.available_observation_count == 20

    handoff_service = Ft012HandoffService(uow=uow)
    before_review = await handoff_service.get(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )
    assert before_review.ready is False
    assert before_review.reason == "EXIT_REVIEW_MISSING"

    review_service = ExitReviewService(
        uow=uow,
        trade_reader=trade_reader,
        planning_reader=planning_reader,
        market_data_reader=market_reader,
        clock=lambda: REVIEW_AT,
    )
    review, draft = await review_service.get_or_create_draft(
        workspace_id=workspace_id,
        observation_id=observation.id,
        actor_id=actor_id,
    )
    assert review.post_trade_observation_id == observation.id
    assert draft.status is ExitReviewStatus.DRAFT

    finalized = await review_service.finalize(
        workspace_id=workspace_id,
        review_id=review.id,
        version_id=draft.id,
        actor_id=actor_id,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="Exit followed the approved plan and preserved risk discipline.",
    )
    assert finalized.status is ExitReviewStatus.FINALIZED
    assert finalized.input_fingerprint is not None

    handoff = await handoff_service.get(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )
    assert handoff.ready is True
    assert handoff.reason == "READY"
    assert handoff.post_trade_observation_id == observation.id
    assert handoff.exit_review_id == review.id
    assert handoff.exit_review_version_id == finalized.id

    assert planning.trade_plan_id == trade_plan_id
    assert planning.trade_plan_version_id == trade_plan_version_id
