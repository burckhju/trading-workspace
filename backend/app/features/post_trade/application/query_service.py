"""Read-side application service for FT-011 Post Trade."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.post_trade.application.ports import (
    HistoricalPlanningContextReader,
    HistoricalProductContextReader,
    PlanningContext,
    ProductContext,
    TradeExitContext,
    TradeExitContextReader,
)
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewVersion,
    PostTradeObservation,
)
from app.features.post_trade.persistence.unit_of_work import (
    PostTradeLearningUnitOfWork,
)


@dataclass(frozen=True, slots=True)
class ObservationView:
    observation: PostTradeObservation
    trade: TradeExitContext
    planning: PlanningContext
    product: ProductContext | None


@dataclass(frozen=True, slots=True)
class ExitReviewView:
    observation: PostTradeObservation
    review: ExitReview
    version: ExitReviewVersion


class PostTradeQueryService:
    def __init__(
        self,
        *,
        uow: PostTradeLearningUnitOfWork,
        trade_reader: TradeExitContextReader,
        planning_reader: HistoricalPlanningContextReader,
        product_reader: HistoricalProductContextReader,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._planning_reader = planning_reader
        self._product_reader = product_reader

    async def get_observation_for_trade(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> PostTradeObservation | None:
        async with self._uow:
            return await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )

    async def get_observation_view(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> ObservationView | None:
        async with self._uow:
            observation = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )
            if observation is None:
                return None

            trade = await self._trade_reader.get(
                workspace_id=workspace_id,
                trade_id=trade_id,
            )
            if trade is None:
                return None

            planning = await self._planning_reader.get(
                workspace_id=workspace_id,
                trade_id=trade_id,
            )
            product = await self._product_reader.get(
                workspace_id=workspace_id,
                trade_id=trade_id,
            )

            return ObservationView(
                observation=observation,
                trade=trade,
                planning=planning,
                product=product,
            )

    async def get_latest_exit_review(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> ExitReviewView | None:
        async with self._uow:
            observation = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )
            if observation is None:
                return None

            review = await self._uow.exit_reviews.get_for_observation(
                workspace_id,
                observation.id,
            )
            if review is None:
                return None

            version = await self._uow.exit_review_versions.get_latest(review.id)
            if version is None:
                return None

            return ExitReviewView(
                observation=observation,
                review=review,
                version=version,
            )

    async def get_open_draft(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> ExitReviewView | None:
        async with self._uow:
            observation = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )
            if observation is None:
                return None

            review = await self._uow.exit_reviews.get_for_observation(
                workspace_id,
                observation.id,
            )
            if review is None:
                return None

            version = await self._uow.exit_review_versions.get_open_draft(review.id)
            if version is None:
                return None

            return ExitReviewView(
                observation=observation,
                review=review,
                version=version,
            )

    async def list_exit_review_history(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> tuple[ExitReviewView, ...]:
        async with self._uow:
            observation = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )
            if observation is None:
                return ()

            review = await self._uow.exit_reviews.get_for_observation(
                workspace_id,
                observation.id,
            )
            if review is None:
                return ()

            versions = await self._uow.exit_review_versions.list_for_review(review.id)

            return tuple(
                ExitReviewView(
                    observation=observation,
                    review=review,
                    version=version,
                )
                for version in versions
            )
