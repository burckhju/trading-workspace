"""Repository contracts and SQLAlchemy adapters for FT-011 Post Trade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
)
from app.features.post_trade.persistence.mapping import (
    exit_review_from_model,
    exit_review_to_model,
    exit_review_version_from_model,
    exit_review_version_to_model,
    observation_from_model,
    observation_to_model,
)
from app.features.post_trade.persistence.models import (
    ExitReviewModel,
    ExitReviewVersionModel,
    PostTradeObservationModel,
)


class PostTradeObservationRepository(Protocol):
    async def add(self, observation: PostTradeObservation) -> None: ...
    async def get(
        self, workspace_id: UUID, observation_id: UUID
    ) -> PostTradeObservation | None: ...
    async def get_for_trade(
        self, workspace_id: UUID, trade_id: UUID
    ) -> PostTradeObservation | None: ...
    async def replace(self, observation: PostTradeObservation) -> None: ...


class ExitReviewRepository(Protocol):
    async def add(self, review: ExitReview) -> None: ...
    async def get(self, workspace_id: UUID, review_id: UUID) -> ExitReview | None: ...
    async def get_for_observation(
        self, workspace_id: UUID, observation_id: UUID
    ) -> ExitReview | None: ...
    async def lock(self, workspace_id: UUID, review_id: UUID) -> bool: ...


class ExitReviewVersionRepository(Protocol):
    async def add(self, version: ExitReviewVersion) -> None: ...
    async def get(self, version_id: UUID) -> ExitReviewVersion | None: ...
    async def list_for_review(self, exit_review_id: UUID) -> Sequence[ExitReviewVersion]: ...
    async def get_latest(self, exit_review_id: UUID) -> ExitReviewVersion | None: ...
    async def get_current_finalized(self, exit_review_id: UUID) -> ExitReviewVersion | None: ...
    async def get_open_draft(self, exit_review_id: UUID) -> ExitReviewVersion | None: ...
    async def next_version_number(self, workspace_id: UUID, exit_review_id: UUID) -> int: ...
    async def replace(self, version: ExitReviewVersion) -> None: ...


class SqlAlchemyPostTradeObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, observation: PostTradeObservation) -> None:
        self._session.add(observation_to_model(observation))

    async def get(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> PostTradeObservation | None:
        model = await self._session.scalar(
            select(PostTradeObservationModel).where(
                PostTradeObservationModel.workspace_id == workspace_id,
                PostTradeObservationModel.id == observation_id,
            )
        )
        return observation_from_model(model) if model else None

    async def get_for_trade(
        self,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> PostTradeObservation | None:
        model = await self._session.scalar(
            select(PostTradeObservationModel).where(
                PostTradeObservationModel.workspace_id == workspace_id,
                PostTradeObservationModel.trade_id == trade_id,
            )
        )
        return observation_from_model(model) if model else None

    async def replace(self, observation: PostTradeObservation) -> None:
        model = await self._session.scalar(
            select(PostTradeObservationModel).where(
                PostTradeObservationModel.id == observation.id,
                PostTradeObservationModel.workspace_id == observation.workspace_id,
            )
        )
        if model is None:
            raise LookupError("post-trade observation not found")

        model.underlying_listing_id = observation.underlying_listing_id
        model.status = observation.status.value
        model.target_observation_count = observation.target_observation_count
        model.started_at = observation.started_at
        model.started_by = observation.started_by
        model.completed_at = observation.completed_at
        model.created_at = observation.created_at
        model.updated_at = observation.updated_at


class SqlAlchemyExitReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, review: ExitReview) -> None:
        self._session.add(exit_review_to_model(review))

    async def get(
        self,
        workspace_id: UUID,
        review_id: UUID,
    ) -> ExitReview | None:
        model = await self._session.scalar(
            select(ExitReviewModel).where(
                ExitReviewModel.workspace_id == workspace_id,
                ExitReviewModel.id == review_id,
            )
        )
        return exit_review_from_model(model) if model else None

    async def get_for_observation(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> ExitReview | None:
        model = await self._session.scalar(
            select(ExitReviewModel).where(
                ExitReviewModel.workspace_id == workspace_id,
                ExitReviewModel.post_trade_observation_id == observation_id,
            )
        )
        return exit_review_from_model(model) if model else None

    async def lock(
        self,
        workspace_id: UUID,
        review_id: UUID,
    ) -> bool:
        value = await self._session.scalar(
            select(ExitReviewModel.id)
            .where(
                ExitReviewModel.id == review_id,
                ExitReviewModel.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        return value is not None


class SqlAlchemyExitReviewVersionRepository:
    def __init__(
        self,
        session: AsyncSession,
        reviews: ExitReviewRepository,
    ) -> None:
        self._session = session
        self._reviews = reviews

    async def add(self, version: ExitReviewVersion) -> None:
        self._session.add(exit_review_version_to_model(version))

    async def get(
        self,
        version_id: UUID,
    ) -> ExitReviewVersion | None:
        model = await self._session.scalar(
            select(ExitReviewVersionModel).where(ExitReviewVersionModel.id == version_id)
        )
        return exit_review_version_from_model(model) if model else None

    async def list_for_review(
        self,
        exit_review_id: UUID,
    ) -> Sequence[ExitReviewVersion]:
        models = (
            await self._session.scalars(
                select(ExitReviewVersionModel)
                .where(ExitReviewVersionModel.exit_review_id == exit_review_id)
                .order_by(
                    ExitReviewVersionModel.version.desc(),
                    ExitReviewVersionModel.id,
                )
            )
        ).all()
        return tuple(exit_review_version_from_model(model) for model in models)

    async def get_latest(
        self,
        exit_review_id: UUID,
    ) -> ExitReviewVersion | None:
        model = await self._session.scalar(
            select(ExitReviewVersionModel)
            .where(ExitReviewVersionModel.exit_review_id == exit_review_id)
            .order_by(
                ExitReviewVersionModel.version.desc(),
                ExitReviewVersionModel.id,
            )
            .limit(1)
        )
        return exit_review_version_from_model(model) if model else None

    async def get_current_finalized(
        self,
        exit_review_id: UUID,
    ) -> ExitReviewVersion | None:
        model = await self._session.scalar(
            select(ExitReviewVersionModel)
            .where(
                ExitReviewVersionModel.exit_review_id == exit_review_id,
                ExitReviewVersionModel.status == ExitReviewStatus.FINALIZED.value,
                ExitReviewVersionModel.currentness == ExitReviewCurrentness.CURRENT.value,
            )
            .order_by(
                ExitReviewVersionModel.version.desc(),
                ExitReviewVersionModel.id,
            )
            .limit(1)
        )
        return exit_review_version_from_model(model) if model else None

    async def get_open_draft(
        self,
        exit_review_id: UUID,
    ) -> ExitReviewVersion | None:
        model = await self._session.scalar(
            select(ExitReviewVersionModel).where(
                ExitReviewVersionModel.exit_review_id == exit_review_id,
                ExitReviewVersionModel.status == ExitReviewStatus.DRAFT.value,
            )
        )
        return exit_review_version_from_model(model) if model else None

    async def next_version_number(
        self,
        workspace_id: UUID,
        exit_review_id: UUID,
    ) -> int:
        if not await self._reviews.lock(workspace_id, exit_review_id):
            raise LookupError("exit review not found")

        latest = await self._session.scalar(
            select(func.max(ExitReviewVersionModel.version)).where(
                ExitReviewVersionModel.exit_review_id == exit_review_id
            )
        )
        return int(latest or 0) + 1

    async def replace(self, version: ExitReviewVersion) -> None:
        model = await self._session.scalar(
            select(ExitReviewVersionModel).where(
                ExitReviewVersionModel.id == version.id,
                ExitReviewVersionModel.exit_review_id == version.exit_review_id,
            )
        )
        if model is None:
            raise LookupError("exit review version not found")

        model.version = version.version
        model.status = version.status.value
        model.currentness = version.currentness.value
        model.timing = version.timing.value if version.timing else None
        model.process_adherence = (
            version.process_adherence.value if version.process_adherence else None
        )
        model.risk_decision = version.risk_decision.value if version.risk_decision else None
        model.overall_exit_decision = (
            version.overall_exit_decision.value if version.overall_exit_decision else None
        )
        model.rationale = version.rationale
        model.input_fingerprint = version.input_fingerprint
        model.created_at = version.created_at
        model.created_by = version.created_by
        model.finalized_at = version.finalized_at
        model.finalized_by = version.finalized_by
        model.supersedes_version_id = version.supersedes_version_id
        model.stale_at = version.stale_at
        model.stale_reason = version.stale_reason
