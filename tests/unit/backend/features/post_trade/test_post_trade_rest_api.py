"""REST tests for FT-011 Post Trade observation endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.post_trade.api.dependencies import (
    get_post_trade_observation_service,
    get_post_trade_query_service,
)
from app.features.post_trade.api.router import router
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    ProductContext,
    TradeExitContext,
)
from app.features.post_trade.domain import (
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.domain.observation_metrics import (
    build_observation_evidence,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


class _TestQuery:
    """Bridge existing REST mocks to the public query contract."""

    def __init__(self, service):
        self._service = service

    async def get_observation_for_trade(
        self,
        *,
        workspace_id,
        trade_id,
    ):
        return await self._service._uow.observations.get_for_trade(
            workspace_id,
            trade_id,
        )

    async def get_observation_view(
        self,
        *,
        workspace_id,
        trade_id,
    ):
        observation = await self.get_observation_for_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if observation is None:
            return None

        trade = await self._service._trade_reader.get(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if trade is None:
            return None

        from types import SimpleNamespace

        return SimpleNamespace(
            observation=observation,
            trade=trade,
            planning=PlanningContext(
                trade_plan_id=None,
                trade_plan_version_id=None,
                original_stop=Decimal("90"),
                original_targets=(Decimal("120"),),
            ),
            product=ProductContext(
                warrant_id=trade.product_id,
                underlying_id=uuid4(),
                historical_warrant_terms_version_id=uuid4(),
                maturity_date=date(2026, 9, 30),
                historical_underlying_listing_id=(observation.underlying_listing_id),
            ),
        )

    async def get_latest_exit_review(
        self,
        *,
        workspace_id,
        trade_id,
    ):
        observation = await self.get_observation_for_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if observation is None:
            return None

        review = await self._service._uow.exit_reviews.get_for_observation(
            workspace_id,
            observation.id,
        )
        if review is None:
            return None

        version = await self._service._uow.exit_review_versions.get_latest(review.id)
        if version is None:
            return None

        from types import SimpleNamespace

        return SimpleNamespace(
            observation=observation,
            review=review,
            version=version,
        )

    async def get_open_draft(
        self,
        *,
        workspace_id,
        trade_id,
    ):
        observation = await self.get_observation_for_trade(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if observation is None:
            return None

        review = await self._service._uow.exit_reviews.get_for_observation(
            workspace_id,
            observation.id,
        )
        if review is None:
            return None

        version = await self._service._uow.exit_review_versions.get_open_draft(review.id)
        if version is None:
            return None

        from types import SimpleNamespace

        return SimpleNamespace(
            observation=observation,
            review=review,
            version=version,
        )

    async def list_exit_review_history(
        self,
        *,
        workspace_id,
        trade_id,
    ):
        latest = await self.get_latest_exit_review(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if latest is None:
            return ()

        versions = await self._service._uow.exit_review_versions.list_for_review(latest.review.id)

        from types import SimpleNamespace

        return tuple(
            SimpleNamespace(
                observation=latest.observation,
                review=latest.review,
                version=version,
            )
            for version in versions
        )


def _app(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_post_trade_observation_service] = lambda: service
    app.dependency_overrides[get_post_trade_query_service] = lambda: _TestQuery(service)
    return app


def _observation():
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.ACTIVE,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_get_observation_returns_progress() -> None:
    observation = _observation()

    evidence = build_observation_evidence(
        (
            DailyObservation(
                listing_id=observation.underlying_listing_id,
                trading_date=date(2026, 8, 19),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("90"),
                close=Decimal("105"),
                adjusted_close=None,
                quality_status="VALID",
            ),
        ),
        full_exit_at=NOW,
        target_count=20,
    )

    service = MagicMock()
    service._uow = MagicMock()
    service._uow.observations = MagicMock()
    service._uow.observations.get_for_trade = AsyncMock(return_value=observation)
    service.refresh = AsyncMock(return_value=(observation, evidence))

    client = TestClient(_app(service))

    response = client.get(f"/api/v1/post-trade/trades/{observation.trade_id}/observation")

    assert response.status_code == 200
    payload = response.json()

    assert payload["id"] == str(observation.id)
    assert payload["available_observation_count"] == 1
    assert payload["missing_observation_count"] == 19
    assert payload["is_complete"] is False


def test_get_observation_evidence_separates_actual_and_counterfactual() -> None:
    observation = _observation()

    evidence = build_observation_evidence(
        (
            DailyObservation(
                listing_id=observation.underlying_listing_id,
                trading_date=date(2026, 8, 19),
                open=Decimal("100"),
                high=Decimal("115"),
                low=Decimal("95"),
                close=Decimal("110"),
                adjusted_close=None,
                quality_status="VALID",
            ),
        ),
        full_exit_at=NOW,
        target_count=20,
    )

    trade = TradeExitContext(
        workspace_id=uuid4(),
        trade_id=observation.trade_id,
        product_id=uuid4(),
        is_fully_closed=True,
        full_exit_at=NOW,
        realized_gross_pnl=Decimal("123.45"),
        executions=(),
        management_events=(),
    )

    service = MagicMock()
    service._uow = MagicMock()
    service._uow.observations = MagicMock()
    service._uow.observations.get_for_trade = AsyncMock(return_value=observation)
    service.refresh = AsyncMock(return_value=(observation, evidence))
    service._trade_reader = MagicMock()
    service._trade_reader.get = AsyncMock(return_value=trade)

    client = TestClient(_app(service))

    response = client.get(f"/api/v1/post-trade/trades/{observation.trade_id}/observation/evidence")

    assert response.status_code == 200
    payload = response.json()

    assert "actual_exit" in payload
    assert "counterfactual" in payload
    assert payload["actual_exit"]["realized_gross_pnl"] == "123.45"
    assert payload["counterfactual"]["available_observation_count"] == 1
