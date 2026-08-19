"""REST tests for FT-011 ExitReview endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.post_trade.api.dependencies import (
    get_exit_review_service,
    get_post_trade_query_service,
)
from app.features.post_trade.api.router import router
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
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
    app.dependency_overrides[get_exit_review_service] = lambda: service
    app.dependency_overrides[get_post_trade_query_service] = lambda: _TestQuery(service)
    return app


def _observation():
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.COMPLETED,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


def _review(observation):
    return ExitReview(
        id=uuid4(),
        workspace_id=observation.workspace_id,
        post_trade_observation_id=observation.id,
        created_at=NOW,
        created_by=uuid4(),
    )


def _draft(review):
    return ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.DRAFT,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.ACCEPTABLE,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="ok",
        input_fingerprint=None,
        created_at=NOW,
        created_by=uuid4(),
    )


def _service(observation, review, draft):
    service = MagicMock()
    service._uow = MagicMock()

    service._uow.observations = MagicMock()
    service._uow.observations.get_for_trade = AsyncMock(return_value=observation)

    service._uow.exit_reviews = MagicMock()
    service._uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)

    service._uow.exit_review_versions = MagicMock()
    service._uow.exit_review_versions.get_latest = AsyncMock(return_value=draft)
    service._uow.exit_review_versions.get_open_draft = AsyncMock(return_value=draft)
    service._uow.exit_review_versions.list_for_review = AsyncMock(return_value=(draft,))

    return service


def test_create_exit_review_draft_returns_201() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    service = _service(observation, review, draft)
    service.get_or_create_draft = AsyncMock(return_value=(review, draft))

    client = TestClient(_app(service))

    response = client.post(f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review")

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"


def test_get_exit_review_returns_latest() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    service = _service(observation, review, draft)

    client = TestClient(_app(service))

    response = client.get(f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review")

    assert response.status_code == 200
    assert response.json()["current_version_id"] == str(draft.id)


def test_update_draft_calls_service() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    service = _service(observation, review, draft)
    service.update_draft = AsyncMock(return_value=draft)

    client = TestClient(_app(service))

    response = client.put(
        f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review/draft",
        json={
            "timing": "GOOD",
            "process_adherence": "ACCEPTABLE",
            "risk_decision": "GOOD",
            "overall_exit_decision": "ACCEPTABLE",
            "rationale": "ok",
        },
    )

    assert response.status_code == 200
    service.update_draft.assert_awaited_once()


def test_finalize_returns_finalized_version() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    finalized = draft.finalize(
        timing=draft.timing,
        process_adherence=draft.process_adherence,
        risk_decision=draft.risk_decision,
        overall_exit_decision=draft.overall_exit_decision,
        rationale=draft.rationale,
        input_fingerprint="a" * 64,
        finalized_at=NOW,
        finalized_by=uuid4(),
    )

    service = _service(observation, review, draft)
    service.finalize = AsyncMock(return_value=finalized)

    client = TestClient(_app(service))

    response = client.post(f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review/finalize")

    assert response.status_code == 200
    assert response.json()["status"] == "FINALIZED"
    assert response.json()["currentness"] == "CURRENT"


def test_revalidate_returns_stale_version() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    finalized = draft.finalize(
        timing=draft.timing,
        process_adherence=draft.process_adherence,
        risk_decision=draft.risk_decision,
        overall_exit_decision=draft.overall_exit_decision,
        rationale=draft.rationale,
        input_fingerprint="a" * 64,
        finalized_at=NOW,
        finalized_by=uuid4(),
    )
    stale = finalized.mark_stale(
        stale_at=NOW,
        stale_reason="changed",
    )

    service = _service(observation, review, draft)
    service.refresh_currentness = AsyncMock(return_value=stale)

    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review/revalidate"
    )

    assert response.status_code == 200
    assert response.json()["currentness"] == "STALE"


def test_history_returns_versions() -> None:
    observation = _observation()
    review = _review(observation)
    draft = _draft(review)

    service = _service(observation, review, draft)

    client = TestClient(_app(service))

    response = client.get(f"/api/v1/post-trade/trades/{observation.trade_id}/exit-review/history")

    assert response.status_code == 200
    assert len(response.json()) == 1
