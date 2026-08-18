"""Application service for FT-011 ExitReview lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.post_trade.application.input_fingerprint import (
    build_exit_review_input_fingerprint,
)
from app.features.post_trade.application.ports import (
    HistoricalPlanningContextReader,
    ObservationMarketDataReader,
    PlanningContext,
    TradeExitContext,
    TradeExitContextReader,
)
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
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


class ExitReviewServiceError(RuntimeError):
    code = "EXIT_REVIEW_ERROR"


class ExitReviewNotFoundError(ExitReviewServiceError):
    code = "EXIT_REVIEW_NOT_FOUND"


class ExitReviewObservationIncompleteError(ExitReviewServiceError):
    code = "EXIT_REVIEW_OBSERVATION_INCOMPLETE"


class ExitReviewIncompleteError(ExitReviewServiceError):
    code = "EXIT_REVIEW_INCOMPLETE"


class ExitReviewAlreadyFinalizedError(ExitReviewServiceError):
    code = "EXIT_REVIEW_ALREADY_FINALIZED"


class ExitReviewService:
    def __init__(
        self,
        *,
        uow: PostTradeLearningUnitOfWork,
        trade_reader: TradeExitContextReader,
        planning_reader: HistoricalPlanningContextReader,
        market_data_reader: ObservationMarketDataReader,
        clock: Clock = lambda: datetime.now(UTC),
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._planning_reader = planning_reader
        self._market_data_reader = market_data_reader
        self._clock = clock
        self._id_factory = id_factory

    async def get_or_create_draft(
        self,
        *,
        workspace_id: UUID,
        observation_id: UUID,
        actor_id: UUID,
    ) -> tuple[ExitReview, ExitReviewVersion]:
        now = self._clock()

        async with self._uow:
            observation = await self._uow.observations.get(
                workspace_id,
                observation_id,
            )
            if observation is None:
                raise ExitReviewNotFoundError("post-trade observation not found")

            if observation.status is not PostTradeObservationStatus.COMPLETED:
                raise ExitReviewObservationIncompleteError(
                    "post-trade observation is not completed"
                )

            review = await self._uow.exit_reviews.get_for_observation(
                workspace_id,
                observation_id,
            )

            if review is None:
                review = ExitReview(
                    id=self._id_factory(),
                    workspace_id=workspace_id,
                    post_trade_observation_id=observation_id,
                    created_at=now,
                    created_by=actor_id,
                )
                await self._uow.exit_reviews.add(review)
                await self._uow.flush()

            existing_draft = await self._uow.exit_review_versions.get_open_draft(review.id)
            if existing_draft is not None:
                return review, existing_draft

            version_number = await self._uow.exit_review_versions.next_version_number(
                workspace_id,
                review.id,
            )

            latest = await self._uow.exit_review_versions.get_latest(review.id)

            draft = ExitReviewVersion(
                id=self._id_factory(),
                exit_review_id=review.id,
                version=version_number,
                status=ExitReviewStatus.DRAFT,
                currentness=ExitReviewCurrentness.CURRENT,
                timing=None,
                process_adherence=None,
                risk_decision=None,
                overall_exit_decision=None,
                rationale=None,
                input_fingerprint=None,
                created_at=now,
                created_by=actor_id,
                supersedes_version_id=(latest.id if latest is not None else None),
            )

            await self._uow.exit_review_versions.add(draft)
            await self._uow.commit()

            return review, draft

    async def update_draft(
        self,
        *,
        workspace_id: UUID,
        review_id: UUID,
        version_id: UUID,
        timing: ExitReviewAssessment,
        process_adherence: ExitReviewAssessment,
        risk_decision: ExitReviewAssessment,
        overall_exit_decision: ExitReviewAssessment,
        rationale: str,
    ) -> ExitReviewVersion:
        async with self._uow:
            review = await self._uow.exit_reviews.get(
                workspace_id,
                review_id,
            )
            if review is None:
                raise ExitReviewNotFoundError("exit review not found")

            version = await self._uow.exit_review_versions.get(version_id)
            if version is None or version.exit_review_id != review.id:
                raise ExitReviewNotFoundError("exit review version not found")

            if version.status is not ExitReviewStatus.DRAFT:
                raise ExitReviewAlreadyFinalizedError("exit review version is not editable")

            updated = ExitReviewVersion(
                id=version.id,
                exit_review_id=version.exit_review_id,
                version=version.version,
                status=version.status,
                currentness=version.currentness,
                timing=timing,
                process_adherence=process_adherence,
                risk_decision=risk_decision,
                overall_exit_decision=overall_exit_decision,
                rationale=rationale,
                input_fingerprint=None,
                created_at=version.created_at,
                created_by=version.created_by,
                finalized_at=None,
                finalized_by=None,
                supersedes_version_id=version.supersedes_version_id,
                stale_at=None,
                stale_reason=None,
            )

            await self._uow.exit_review_versions.replace(updated)
            await self._uow.commit()

            return updated

    async def finalize(
        self,
        *,
        workspace_id: UUID,
        review_id: UUID,
        version_id: UUID,
        actor_id: UUID,
        timing: ExitReviewAssessment,
        process_adherence: ExitReviewAssessment,
        risk_decision: ExitReviewAssessment,
        overall_exit_decision: ExitReviewAssessment,
        rationale: str,
    ) -> ExitReviewVersion:
        now = self._clock()

        async with self._uow:
            review = await self._uow.exit_reviews.get(
                workspace_id,
                review_id,
            )
            if review is None:
                raise ExitReviewNotFoundError("exit review not found")

            version = await self._uow.exit_review_versions.get(version_id)
            if version is None or version.exit_review_id != review.id:
                raise ExitReviewNotFoundError("exit review version not found")

            if version.status is ExitReviewStatus.FINALIZED:
                raise ExitReviewAlreadyFinalizedError("exit review version is already finalized")

            observation = await self._uow.observations.get(
                workspace_id,
                review.post_trade_observation_id,
            )
            if observation is None:
                raise ExitReviewNotFoundError("post-trade observation not found")

            if observation.status is not PostTradeObservationStatus.COMPLETED:
                raise ExitReviewObservationIncompleteError(
                    "post-trade observation is not completed"
                )

            trade, planning, evidence = await self._review_inputs(
                workspace_id=workspace_id,
                observation=observation,
                now=now,
            )

            if not evidence.horizon_complete:
                raise ExitReviewObservationIncompleteError("observation evidence is incomplete")

            fingerprint = build_exit_review_input_fingerprint(
                trade=trade,
                planning=planning,
                evidence=evidence,
            )

            finalized = version.finalize(
                timing=timing,
                process_adherence=process_adherence,
                risk_decision=risk_decision,
                overall_exit_decision=overall_exit_decision,
                rationale=rationale,
                input_fingerprint=fingerprint,
                finalized_at=now,
                finalized_by=actor_id,
            )

            await self._uow.exit_review_versions.replace(finalized)
            await self._uow.commit()

            return finalized

    async def refresh_currentness(
        self,
        *,
        workspace_id: UUID,
        review_id: UUID,
    ) -> ExitReviewVersion | None:
        now = self._clock()

        async with self._uow:
            review = await self._uow.exit_reviews.get(
                workspace_id,
                review_id,
            )
            if review is None:
                raise ExitReviewNotFoundError("exit review not found")

            current = await self._uow.exit_review_versions.get_current_finalized(review.id)
            if current is None:
                return None

            observation = await self._uow.observations.get(
                workspace_id,
                review.post_trade_observation_id,
            )
            if observation is None:
                raise ExitReviewNotFoundError("post-trade observation not found")

            trade, planning, evidence = await self._review_inputs(
                workspace_id=workspace_id,
                observation=observation,
                now=now,
            )

            fingerprint = build_exit_review_input_fingerprint(
                trade=trade,
                planning=planning,
                evidence=evidence,
            )

            if fingerprint == current.input_fingerprint:
                return current

            stale = current.mark_stale(
                stale_at=now,
                stale_reason="FT-011 relevant input fingerprint changed",
            )

            await self._uow.exit_review_versions.replace(stale)
            await self._uow.commit()

            return stale

    async def _review_inputs(
        self,
        *,
        workspace_id: UUID,
        observation: PostTradeObservation,
        now: datetime,
    ) -> tuple[TradeExitContext, PlanningContext, ObservationEvidence]:
        trade = await self._trade_reader.get(
            workspace_id=workspace_id,
            trade_id=observation.trade_id,
        )
        if trade is None or trade.full_exit_at is None:
            raise ExitReviewNotFoundError("trade exit context not found")

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

        return trade, planning, evidence
