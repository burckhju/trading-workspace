"""FT-011 to FT-012 handoff gate."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.post_trade.domain import (
    ExitReviewCurrentness,
    ExitReviewStatus,
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.unit_of_work import (
    PostTradeLearningUnitOfWork,
)


@dataclass(frozen=True, slots=True)
class Ft012Handoff:
    ready: bool
    reason: str
    post_trade_observation_id: UUID | None
    exit_review_id: UUID | None
    exit_review_version_id: UUID | None


class Ft012HandoffService:
    def __init__(
        self,
        *,
        uow: PostTradeLearningUnitOfWork,
    ) -> None:
        self._uow = uow

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Ft012Handoff:
        async with self._uow:
            observation = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )

            if observation is None:
                return Ft012Handoff(
                    ready=False,
                    reason="POST_TRADE_OBSERVATION_MISSING",
                    post_trade_observation_id=None,
                    exit_review_id=None,
                    exit_review_version_id=None,
                )

            if observation.status is not PostTradeObservationStatus.COMPLETED:
                return Ft012Handoff(
                    ready=False,
                    reason="POST_TRADE_OBSERVATION_INCOMPLETE",
                    post_trade_observation_id=observation.id,
                    exit_review_id=None,
                    exit_review_version_id=None,
                )

            review = await self._uow.exit_reviews.get_for_observation(
                workspace_id,
                observation.id,
            )

            if review is None:
                return Ft012Handoff(
                    ready=False,
                    reason="EXIT_REVIEW_MISSING",
                    post_trade_observation_id=observation.id,
                    exit_review_id=None,
                    exit_review_version_id=None,
                )

            version = await self._uow.exit_review_versions.get_latest(review.id)

            if version is None:
                return Ft012Handoff(
                    ready=False,
                    reason="EXIT_REVIEW_VERSION_MISSING",
                    post_trade_observation_id=observation.id,
                    exit_review_id=review.id,
                    exit_review_version_id=None,
                )

            if version.status is not ExitReviewStatus.FINALIZED:
                return Ft012Handoff(
                    ready=False,
                    reason="EXIT_REVIEW_NOT_FINALIZED",
                    post_trade_observation_id=observation.id,
                    exit_review_id=review.id,
                    exit_review_version_id=version.id,
                )

            if version.currentness is not ExitReviewCurrentness.CURRENT:
                return Ft012Handoff(
                    ready=False,
                    reason="EXIT_REVIEW_STALE",
                    post_trade_observation_id=observation.id,
                    exit_review_id=review.id,
                    exit_review_version_id=version.id,
                )

            return Ft012Handoff(
                ready=True,
                reason="READY",
                post_trade_observation_id=observation.id,
                exit_review_id=review.id,
                exit_review_version_id=version.id,
            )
