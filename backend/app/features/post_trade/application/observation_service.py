"""Application service for FT-011 post-trade observation lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.features.post_trade.application.ports import (
    HistoricalPlanningContextReader,
    HistoricalProductContextReader,
    ObservationMarketDataReader,
    TradeExitContextReader,
    UnderlyingListingResolver,
)
from app.features.post_trade.domain import (
    FT011_V1_OBSERVATION_COUNT,
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.domain.observation_metrics import (
    ObservationEvidence,
    build_observation_evidence,
)
from app.features.post_trade.persistence.unit_of_work import (
    PostTradeLearningUnitOfWork,
)

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class PostTradeObservationError(RuntimeError):
    code = "POST_TRADE_OBSERVATION_ERROR"


class PostTradeNotEligibleError(PostTradeObservationError):
    code = "POST_TRADE_NOT_ELIGIBLE"


class PostTradeObservationExistsError(PostTradeObservationError):
    code = "POST_TRADE_OBSERVATION_ALREADY_EXISTS"


class PostTradeContextNotFoundError(PostTradeObservationError):
    code = "POST_TRADE_CONTEXT_NOT_FOUND"


class PostTradeListingResolutionError(PostTradeObservationError):
    code = "POST_TRADE_LISTING_NOT_RESOLVABLE"


class PostTradeObservationService:
    def __init__(
        self,
        *,
        uow: PostTradeLearningUnitOfWork,
        trade_reader: TradeExitContextReader,
        planning_reader: HistoricalPlanningContextReader,
        product_reader: HistoricalProductContextReader,
        listing_resolver: UnderlyingListingResolver,
        market_data_reader: ObservationMarketDataReader,
        clock: Clock = lambda: datetime.now(UTC),
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._planning_reader = planning_reader
        self._product_reader = product_reader
        self._listing_resolver = listing_resolver
        self._market_data_reader = market_data_reader
        self._clock = clock
        self._id_factory = id_factory

    async def start(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        actor_id: UUID,
    ) -> PostTradeObservation:
        now = self._clock()

        trade = await self._trade_reader.get(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if trade is None:
            raise PostTradeContextNotFoundError("trade context not found")

        if not trade.is_fully_closed or trade.full_exit_at is None:
            raise PostTradeNotEligibleError("trade is not fully economically closed")

        product = await self._product_reader.get(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if product is None:
            raise PostTradeContextNotFoundError("historical product context not found")

        try:
            listing_id = await self._listing_resolver.resolve(
                workspace_id=workspace_id,
                product_context=product,
                observation_started_at=now,
            )
        except (LookupError, ValueError) as exc:
            raise PostTradeListingResolutionError(str(exc)) from exc

        async with self._uow:
            existing = await self._uow.observations.get_for_trade(
                workspace_id,
                trade_id,
            )
            if existing is not None:
                raise PostTradeObservationExistsError("post-trade observation already exists")

            observation = PostTradeObservation(
                id=self._id_factory(),
                workspace_id=workspace_id,
                trade_id=trade_id,
                underlying_listing_id=listing_id,
                status=PostTradeObservationStatus.ACTIVE,
                target_observation_count=FT011_V1_OBSERVATION_COUNT,
                started_at=now,
                started_by=actor_id,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )

            await self._uow.observations.add(observation)
            await self._uow.commit()

        return observation

    async def refresh(
        self,
        *,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> tuple[PostTradeObservation, ObservationEvidence]:
        now = self._clock()

        async with self._uow:
            observation = await self._uow.observations.get(
                workspace_id,
                observation_id,
            )
            if observation is None:
                raise PostTradeContextNotFoundError("post-trade observation not found")

            trade = await self._trade_reader.get(
                workspace_id=workspace_id,
                trade_id=observation.trade_id,
            )
            if trade is None or trade.full_exit_at is None:
                raise PostTradeContextNotFoundError("trade exit context not found")

            planning = await self._planning_reader.get(
                workspace_id=workspace_id,
                trade_id=observation.trade_id,
            )

            prices = await self._market_data_reader.list_range(
                workspace_id=workspace_id,
                listing_id=observation.underlying_listing_id,
                start_date=trade.full_exit_at.date(),
                end_date=now.date(),
            )

            evidence = build_observation_evidence(
                prices,
                full_exit_at=trade.full_exit_at,
                target_count=observation.target_observation_count,
                targets=planning.original_targets,
                stop=planning.original_stop,
            )

            updated = observation

            if (
                observation.status is PostTradeObservationStatus.ACTIVE
                and evidence.horizon_complete
            ):
                completed_at = self._completion_timestamp(
                    evidence=evidence,
                    fallback=now,
                )
                updated = observation.complete(completed_at=completed_at)
                await self._uow.observations.replace(updated)
                await self._uow.commit()

            return updated, evidence

    @staticmethod
    def _completion_timestamp(
        *,
        evidence: ObservationEvidence,
        fallback: datetime,
    ) -> datetime:
        if evidence.final_close is None:
            return fallback

        completion_date = evidence.final_close.trading_date

        return datetime.combine(
            completion_date,
            datetime.min.time(),
            tzinfo=UTC,
        ) + timedelta(days=1)
