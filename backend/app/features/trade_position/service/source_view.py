"""Bounded read-only composition of existing owners; no money or quality model.

Each method owns one short PostgreSQL snapshot. Different sections deliberately
have different read windows. No command-side trade repository (FOR UPDATE),
provider, materialization or currentness refresh is used.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.candidate.persistence.models import CandidateEvaluationSourceModel
from app.features.learning.domain import FT011Evidence, TradeJournalVersion
from app.features.learning.persistence.ft011_materialization_repository import (
    SqlAlchemyFt011MaterializationRepository,
)
from app.features.learning.persistence.journal_repository import SqlAlchemyJournalRepository
from app.features.learning.persistence.lesson_evidence_read_repository import (
    HistoricalLessonEvidenceReference,
    SqlAlchemyLessonEvidenceReadRepository,
)
from app.features.learning.persistence.models import (
    FT011EvidenceModel,
    LearningEvidenceModel,
    LessonEvidenceLinkModel,
    LessonModel,
    LessonVersionModel,
    TradeJournalModel,
    TradeJournalVersionEvidenceModel,
    TradeJournalVersionModel,
)
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.post_trade.application.exit_review_service import ExitReviewService
from app.features.post_trade.application.query_service import ExitReviewView, PostTradeQueryService
from app.features.post_trade.application.read_adapters import (
    SqlAlchemyHistoricalPlanningContextReader,
    SqlAlchemyHistoricalProductContextReader,
    SqlAlchemyObservationMarketDataReader,
    SqlAlchemyTradeExitContextReader,
)
from app.features.post_trade.persistence.models import (
    ExitReviewModel,
    ExitReviewVersionModel,
    PostTradeObservationModel,
)
from app.features.post_trade.persistence.unit_of_work import SqlAlchemyPostTradeLearningUnitOfWork
from app.features.product.persistence.models import WarrantModel
from app.features.trade_plan.persistence.models import (
    TradePlanEventModel,
    TradePlanModel,
    TradePlanTargetModel,
)
from app.features.trade_plan.service.queries import TradePlanQueryService, TradePlanVersionView
from app.features.trade_position.domain.currency import (
    CurrencyTradeScope,
    ExecutionCurrencyConfirmation,
    ExecutionCurrencyResolution,
)
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidenceLimitExceeded,
)
from app.features.trade_position.domain.currency_resolution import (
    CurrencyExecution,
    CurrencyResolutionLimitExceeded,
    resolve_execution_currencies,
)
from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.domain.timeline import (
    TradeTimelineEntry,
    TradeTimelineEntryKind,
    compose_trade_timeline,
)
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.persistence.currency_models import (
    ExecutionCurrencyConfirmationModel,
)
from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    TradeManagementEventModel,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
    SqlAlchemyTradeManagementEventRepository,
)
from app.features.trade_position.service.resolvers import SqlAlchemyWorkspaceSelectionResolver

MAX_FACTS = 2_000
MAX_VERSIONS = 100
MAX_LINKS = 1_000
MAX_CURRENCY_PROVENANCE_LINKS = 100_000


@dataclass(frozen=True)
class _ProductCurrencyScope:
    """Transient resolver scope; this is neither a Trade nor a persisted identity."""

    id: UUID
    workspace_id: UUID
    product_id: UUID


@dataclass(frozen=True)
class _CurrencyPreviewContext:
    """Only resolver inputs: no invented execution quantity, price or confirmation."""

    id: UUID
    trade_id: UUID
    product_id: UUID
    side: ExecutionSide
    executed_at: datetime
    recorded_at: datetime
    executed_on: date | None
    execution_timezone: str | None
    supersedes_execution_id: None = None


@dataclass(frozen=True)
class SourceSnapshot[T]:
    data: T
    read_started_at: datetime
    read_completed_at: datetime


@dataclass(frozen=True)
class TradeSourceCore:
    trade: Trade
    product_name: str | None
    state: str
    open_quantity: int | None
    timeline: tuple[TradeTimelineEntry, ...]
    currency_history: tuple[ExecutionCurrencyConfirmation, ...]


@dataclass(frozen=True)
class ReviewSources:
    history: tuple[ExitReviewView, ...]
    selected: ExitReviewView | None
    source_currentness: str
    checked_at: datetime


@dataclass(frozen=True)
class JournalSources:
    history: tuple[TradeJournalVersion, ...]
    selected: TradeJournalVersion | None
    source_currentness: str
    checked_at: datetime


@dataclass(frozen=True)
class EvidenceSource:
    evidence_id: UUID
    evidence_type: str
    created_at: datetime
    review_version_id: UUID | None
    journal_version_id: UUID | None
    source_bound: bool
    lesson_links: tuple[HistoricalLessonEvidenceReference, ...]


def source_error(code: str, message: str, status: int) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def select_version[T](
    values: tuple[T, ...], pin: UUID | None, identity: Callable[[T], UUID]
) -> T | None:
    """Explicit pins never fall back; caller supplies already scoped owner values."""
    if pin is None:
        return values[0] if values else None
    for value in values:
        if identity(value) == pin:
            return value
    raise source_error("SOURCE_VERSION_NOT_FOUND", "Version gehört nicht zu diesem Trade.", 404)


class TradeSourceReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        async with (
            AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session,
            session.begin(),
        ):
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            yield session

    @staticmethod
    async def _bounded(session: AsyncSession, statement: Select[tuple[UUID]], limit: int) -> None:
        if len((await session.scalars(statement.limit(limit + 1))).all()) > limit:
            raise source_error(
                "SOURCE_RESOURCE_LIMIT",
                "Die vollständigen Quellen überschreiten die Lesegrenze; nichts abgeschnitten.",
                413,
            )

    @staticmethod
    async def _trade(session: AsyncSession, workspace_id: UUID, trade_id: UUID) -> Trade:
        trade = await SqlAlchemyReadOnlyTradeRepository(session).get(workspace_id, trade_id)
        if trade is None:
            raise source_error("TRADE_NOT_FOUND", "Trade nicht gefunden.", 404)
        return trade

    async def execution_currency_preview(
        self,
        workspace_id: UUID,
        *,
        side: ExecutionSide,
        executed_at: datetime,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
        trade_id: UUID | None = None,
        product_id: UUID | None = None,
    ) -> ExecutionCurrencyResolution:
        """Resolve the proposed time in one existing bounded, read-only snapshot.

        The preview is never a new confirmation or a promise about a future write.
        The normal capture independently resolves its committed sources again.
        """
        if (trade_id is None) == (product_id is None):
            raise ValueError("Currency preview requires exactly one trade or product")
        if product_id is not None and side is not ExecutionSide.BUY:
            raise ValueError("An initial product currency preview requires BUY")
        async with self._session() as session:
            scope: CurrencyTradeScope
            executions: list[CurrencyExecution] = []
            current: dict[UUID, ExecutionCurrencyConfirmation] = {}
            if trade_id is not None:
                trade = await self._trade(session, workspace_id, trade_id)
                if trade.cancelled_at is not None:
                    raise source_error("TRADE_CANCELLED", "Dieser Trade wurde storniert.", 409)
                scope = trade
                await self._bounded(
                    session,
                    select(ExecutionRecordModel.id).where(
                        ExecutionRecordModel.trade_id == trade_id
                    ),
                    MAX_FACTS,
                )
                await self._bounded(
                    session,
                    select(ExecutionCurrencyConfirmationModel.id).where(
                        ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                        ExecutionCurrencyConfirmationModel.trade_id == trade_id,
                    ),
                    MAX_FACTS,
                )
                executions.extend(
                    await SqlAlchemyExecutionRecordRepository(session).list_for_trade(trade_id)
                )
                current = await SqlAlchemyExecutionCurrencyConfirmationRepository(
                    session
                ).current_for_trade(workspace_id, trade_id)
            else:
                found = await session.scalar(
                    select(WarrantModel.id).where(
                        WarrantModel.workspace_id == workspace_id,
                        WarrantModel.id == product_id,
                    )
                )
                if found is None:
                    raise source_error(
                        "WARRANT_NOT_FOUND",
                        "Produkt in diesem Workspace nicht gefunden.",
                        404,
                    )
                scope = _ProductCurrencyScope(uuid4(), workspace_id, found)
            preview = _CurrencyPreviewContext(
                id=uuid4(),
                trade_id=scope.id,
                product_id=scope.product_id,
                side=side,
                executed_at=executed_at,
                recorded_at=datetime.now(UTC),
                executed_on=executed_on,
                execution_timezone=execution_timezone,
            )
            try:
                evidence = await SqlAlchemyCurrencyEvidenceRepository(session).list_for_product(
                    workspace_id, scope.product_id, limit=MAX_FACTS
                )
                if product_id is not None:
                    # Another execution's document never proves this first purchase.
                    evidence = tuple(
                        item for item in evidence if item.kind == "HISTORICAL_LISTINGS"
                    )
                resolutions = resolve_execution_currencies(
                    trade=scope,
                    executions=[*executions, preview],
                    current=current,
                    evidence=evidence,
                    max_provenance_links=MAX_CURRENCY_PROVENANCE_LINKS,
                )
            except (
                CurrencyEvidenceLimitExceeded,
                CurrencyResolutionLimitExceeded,
            ) as error:
                raise source_error(
                    "SOURCE_RESOURCE_LIMIT",
                    "Die vollständigen Währungsquellen überschreiten die sichere Lesegrenze.",
                    413,
                ) from error
            return resolutions[preview.id]

    @staticmethod
    def _review_query(session: AsyncSession) -> PostTradeQueryService:
        trades = SqlAlchemyReadOnlyTradeRepository(session)
        return PostTradeQueryService(
            uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
            trade_reader=SqlAlchemyTradeExitContextReader(session, trades=trades),
            planning_reader=SqlAlchemyHistoricalPlanningContextReader(session, trades=trades),
            product_reader=SqlAlchemyHistoricalProductContextReader(session, trades=trades),
        )

    @staticmethod
    def _inspector(session: AsyncSession) -> ExitReviewService:
        trades = SqlAlchemyReadOnlyTradeRepository(session)
        return ExitReviewService(
            uow=SqlAlchemyPostTradeLearningUnitOfWork(session),
            trade_reader=SqlAlchemyTradeExitContextReader(session, trades=trades),
            planning_reader=SqlAlchemyHistoricalPlanningContextReader(session, trades=trades),
            market_data_reader=SqlAlchemyObservationMarketDataReader(session),
        )

    @staticmethod
    def _review_scope(workspace_id: UUID, trade_id: UUID) -> Select[tuple[UUID]]:
        return (
            select(ExitReviewVersionModel.id)
            .join(ExitReviewModel, ExitReviewModel.id == ExitReviewVersionModel.exit_review_id)
            .join(
                PostTradeObservationModel,
                PostTradeObservationModel.id == ExitReviewModel.post_trade_observation_id,
            )
            .where(
                ExitReviewModel.workspace_id == workspace_id,
                PostTradeObservationModel.workspace_id == workspace_id,
                PostTradeObservationModel.trade_id == trade_id,
            )
        )

    async def _inspection_limits(
        self, session: AsyncSession, workspace_id: UUID, trade_id: UUID, version_id: UUID
    ) -> None:
        for model in (ExecutionRecordModel, TradeManagementEventModel):
            await self._bounded(
                session, select(model.id).where(model.trade_id == trade_id), MAX_FACTS
            )
        trade = await self._trade(session, workspace_id, trade_id)
        # Validate the persisted plan graph before the inspector can hydrate it.
        if trade.trade_plan_id is not None:
            own_plan = await session.scalar(
                select(TradePlanModel.id).where(
                    TradePlanModel.workspace_id == workspace_id,
                    TradePlanModel.id == trade.trade_plan_id,
                )
            )
            if own_plan is None:
                raise source_error(
                    "SOURCE_REFERENCE_MISMATCH", "Planherkunft nicht auflösbar.", 409
                )
        await self._bounded(
            session,
            select(TradePlanTargetModel.id).where(
                TradePlanTargetModel.trade_plan_version_id == trade.trade_plan_version_id
            ),
            MAX_FACTS,
        )
        listing = await session.scalar(
            select(PostTradeObservationModel.underlying_listing_id)
            .join(
                ExitReviewModel,
                ExitReviewModel.post_trade_observation_id == PostTradeObservationModel.id,
            )
            .join(
                ExitReviewVersionModel, ExitReviewVersionModel.exit_review_id == ExitReviewModel.id
            )
            .where(
                PostTradeObservationModel.workspace_id == workspace_id,
                PostTradeObservationModel.trade_id == trade_id,
                ExitReviewModel.workspace_id == workspace_id,
                ExitReviewVersionModel.id == version_id,
            )
        )
        if listing is not None:
            await self._bounded(
                session,
                select(DailyPriceModel.id).where(
                    DailyPriceModel.workspace_id == workspace_id,
                    DailyPriceModel.listing_id == listing,
                ),
                MAX_FACTS,
            )

    async def core(self, workspace_id: UUID, trade_id: UUID) -> SourceSnapshot[TradeSourceCore]:
        started = datetime.now(UTC)
        async with self._session() as session:
            trade = await self._trade(session, workspace_id, trade_id)
            for model in (ExecutionRecordModel, TradeManagementEventModel):
                await self._bounded(
                    session, select(model.id).where(model.trade_id == trade_id), MAX_FACTS
                )
            await self._bounded(
                session,
                select(ExecutionCurrencyConfirmationModel.id).where(
                    ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                    ExecutionCurrencyConfirmationModel.trade_id == trade_id,
                ),
                MAX_FACTS,
            )
            executions = await SqlAlchemyExecutionRecordRepository(session).list_for_trade(trade_id)
            events = await SqlAlchemyTradeManagementEventRepository(session).list_for_trade(
                trade_id
            )
            currency_repo = SqlAlchemyExecutionCurrencyConfirmationRepository(session)
            current = await currency_repo.current_for_trade(workspace_id, trade_id)
            resolution = resolve_execution_currencies(
                trade=trade,
                executions=executions,
                current=current,
                evidence=await SqlAlchemyCurrencyEvidenceRepository(session).list_for_product(
                    workspace_id, trade.product_id, limit=MAX_FACTS
                ),
            )
            executions = [
                replace(
                    item,
                    currency_confirmation=current.get(item.id),
                    currency_resolution=resolution[item.id],
                )
                for item in executions
            ]
            timeline = compose_trade_timeline(
                trade_id=trade_id, executions=executions, management_events=events
            )
            if trade.cancelled_at is not None:
                timeline.append(
                    TradeTimelineEntry(
                        id=trade.id,
                        trade_id=trade.id,
                        occurred_at=trade.cancelled_at,
                        recorded_at=trade.cancelled_at,
                        kind=TradeTimelineEntryKind.CANCELLATION,
                        text_value=trade.cancellation_reason,
                    )
                )
            confirmations = (
                await session.scalars(
                    select(ExecutionCurrencyConfirmationModel)
                    .where(
                        ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                        ExecutionCurrencyConfirmationModel.trade_id == trade_id,
                    )
                    .order_by(
                        ExecutionCurrencyConfirmationModel.confirmed_at,
                        ExecutionCurrencyConfirmationModel.id,
                    )
                )
            ).all()
            position = await SqlAlchemyPositionRepository(session).get_for_trade(
                workspace_id, trade_id
            )
            name = await session.scalar(
                select(WarrantModel.display_name).where(
                    WarrantModel.workspace_id == workspace_id, WarrantModel.id == trade.product_id
                )
            )
            state = (
                "CANCELLED"
                if trade.cancelled_at
                else ("UNKNOWN" if position is None else "CLOSED" if position.is_closed else "OPEN")
            )
            result = TradeSourceCore(
                trade,
                name,
                state,
                None if position is None or trade.cancelled_at else position.open_quantity,
                tuple(
                    sorted(timeline, key=lambda item: (item.occurred_at, item.recorded_at, item.id))
                ),
                tuple(currency_repo._to_domain(item) for item in confirmations),
            )
            return SourceSnapshot(result, started, datetime.now(UTC))

    async def plan(
        self, workspace_id: UUID, trade_id: UUID
    ) -> SourceSnapshot[TradePlanVersionView | None]:
        started = datetime.now(UTC)
        async with self._session() as session:
            trade = await self._trade(session, workspace_id, trade_id)
            if trade.origin is TradeOrigin.EXTERNAL:
                return SourceSnapshot(None, started, datetime.now(UTC))
            assert trade.trade_plan_id is not None and trade.trade_plan_version_id is not None
            assert trade.product_selection_id is not None
            source = await SqlAlchemyWorkspaceSelectionResolver(session).resolve(
                workspace_id, trade.product_selection_id
            )
            if source is None or (
                source.product_id,
                source.trade_plan_id,
                source.trade_plan_version_id,
                source.product_evaluation_id,
            ) != (
                trade.product_id,
                trade.trade_plan_id,
                trade.trade_plan_version_id,
                trade.product_evaluation_id,
            ):
                raise source_error(
                    "SOURCE_REFERENCE_MISMATCH", "Planherkunft nicht auflösbar.", 409
                )
            for model in (TradePlanEventModel, TradePlanTargetModel):
                await self._bounded(
                    session,
                    select(model.id).where(
                        model.trade_plan_version_id == trade.trade_plan_version_id
                    ),
                    MAX_FACTS,
                )
            await self._bounded(
                session,
                select(CandidateEvaluationSourceModel.id)
                .join(
                    TradePlanModel,
                    TradePlanModel.candidate_evaluation_id
                    == CandidateEvaluationSourceModel.evaluation_id,
                )
                .where(
                    TradePlanModel.workspace_id == workspace_id,
                    TradePlanModel.id == trade.trade_plan_id,
                ),
                MAX_FACTS,
            )
            try:
                result = await TradePlanQueryService(session).get_version(
                    workspace_id, trade.trade_plan_id, trade.trade_plan_version_id
                )
            except ValueError as error:
                raise source_error(
                    "SOURCE_REFERENCE_MISMATCH", "Planquelle nicht auflösbar.", 409
                ) from error
            underlying_id = await session.scalar(
                select(WarrantModel.underlying_id).where(
                    WarrantModel.workspace_id == workspace_id, WarrantModel.id == trade.product_id
                )
            )
            if result.plan.underlying_id != underlying_id:
                raise source_error(
                    "SOURCE_REFERENCE_MISMATCH", "Plan und Produkt passen nicht zusammen.", 409
                )
            return SourceSnapshot(result, started, datetime.now(UTC))

    async def reviews(
        self, workspace_id: UUID, trade_id: UUID, version_id: UUID | None = None
    ) -> SourceSnapshot[ReviewSources]:
        started = datetime.now(UTC)
        async with self._session() as session:
            await self._trade(session, workspace_id, trade_id)
            await self._bounded(session, self._review_scope(workspace_id, trade_id), MAX_VERSIONS)
            history = await self._review_query(session).list_exit_review_history(
                workspace_id=workspace_id, trade_id=trade_id
            )
            selected = select_version(history, version_id, lambda item: item.version.id)
            if selected is not None:
                await self._inspection_limits(session, workspace_id, trade_id, selected.version.id)
            state = (
                None
                if selected is None
                else await self._inspector(session).inspect_version_currentness(
                    workspace_id=workspace_id, version_id=selected.version.id
                )
            )
            checked = datetime.now(UTC)
            return SourceSnapshot(
                ReviewSources(history, selected, state.value if state else "UNKNOWN", checked),
                started,
                checked,
            )

    async def journal(
        self, workspace_id: UUID, trade_id: UUID, version_id: UUID | None = None
    ) -> SourceSnapshot[JournalSources]:
        started = datetime.now(UTC)
        async with self._session() as session:
            await self._trade(session, workspace_id, trade_id)
            repo = SqlAlchemyJournalRepository(session)
            journal = await repo.get(workspace_id, trade_id)
            history: tuple[TradeJournalVersion, ...] = ()
            if journal is not None:
                await self._bounded(
                    session,
                    select(TradeJournalVersionModel.id).where(
                        TradeJournalVersionModel.trade_journal_id == journal.id
                    ),
                    MAX_VERSIONS,
                )
                history = tuple(await repo.versions(journal.id))
            selected = select_version(history, version_id, lambda item: item.id)
            state = None
            if selected is not None and selected.source_exit_review_version_id is not None:
                source_id = await session.scalar(
                    self._review_scope(workspace_id, trade_id).where(
                        ExitReviewVersionModel.id == selected.source_exit_review_version_id
                    )
                )
                if source_id is not None:
                    await self._inspection_limits(session, workspace_id, trade_id, source_id)
                    state = await self._inspector(session).inspect_version_currentness(
                        workspace_id=workspace_id, version_id=source_id
                    )
            checked = datetime.now(UTC)
            return SourceSnapshot(
                JournalSources(history, selected, state.value if state else "UNKNOWN", checked),
                started,
                checked,
            )

    async def evidence(
        self, workspace_id: UUID, trade_id: UUID
    ) -> SourceSnapshot[tuple[EvidenceSource, ...]]:
        started = datetime.now(UTC)
        async with self._session() as session:
            await self._trade(session, workspace_id, trade_id)
            await self._bounded(
                session,
                select(FT011EvidenceModel.learning_evidence_id)
                .join(
                    LearningEvidenceModel,
                    LearningEvidenceModel.id == FT011EvidenceModel.learning_evidence_id,
                )
                .where(
                    FT011EvidenceModel.trade_id == trade_id,
                    LearningEvidenceModel.workspace_id == workspace_id,
                ),
                MAX_VERSIONS,
            )
            ft011 = await SqlAlchemyFt011MaterializationRepository(session).list_for_trade(
                workspace_id=workspace_id, trade_id=trade_id
            )
            journals_query = (
                select(
                    LearningEvidenceModel, TradeJournalVersionEvidenceModel.trade_journal_version_id
                )
                .join(
                    TradeJournalVersionEvidenceModel,
                    TradeJournalVersionEvidenceModel.learning_evidence_id
                    == LearningEvidenceModel.id,
                )
                .join(
                    TradeJournalVersionModel,
                    TradeJournalVersionModel.id
                    == TradeJournalVersionEvidenceModel.trade_journal_version_id,
                )
                .join(
                    TradeJournalModel,
                    TradeJournalModel.id == TradeJournalVersionModel.trade_journal_id,
                )
                .where(
                    TradeJournalModel.workspace_id == workspace_id,
                    TradeJournalModel.trade_id == trade_id,
                    LearningEvidenceModel.workspace_id == workspace_id,
                    LearningEvidenceModel.evidence_type == "TRADE_JOURNAL_VERSION",
                )
                .order_by(LearningEvidenceModel.created_at, LearningEvidenceModel.id)
            )
            journals = (await session.execute(journals_query.limit(MAX_VERSIONS + 1))).all()
            if len(journals) + len(ft011) > MAX_VERSIONS:
                raise source_error(
                    "SOURCE_RESOURCE_LIMIT", "Zu viele Evidencequellen; nichts abgeschnitten.", 413
                )
            ids = [value.evidence.id for value in ft011] + [row.id for row, _ in journals]
            await self._bounded(
                session,
                select(LessonEvidenceLinkModel.id)
                .join(
                    LessonVersionModel,
                    LessonVersionModel.id == LessonEvidenceLinkModel.lesson_version_id,
                )
                .join(LessonModel, LessonModel.id == LessonVersionModel.lesson_id)
                .where(
                    LessonModel.workspace_id == workspace_id,
                    LessonEvidenceLinkModel.learning_evidence_id.in_(ids),
                ),
                MAX_LINKS,
            )
            lessons = SqlAlchemyLessonEvidenceReadRepository(session)
            result = []
            for value in ft011:
                source = value.source
                if not isinstance(source, FT011Evidence):
                    raise source_error("SOURCE_REFERENCE_MISMATCH", "Falscher Evidenztyp.", 409)
                bound = (
                    await session.scalar(
                        self._review_scope(workspace_id, trade_id).where(
                            ExitReviewVersionModel.id == source.exit_review_version_id,
                            ExitReviewModel.id == source.exit_review_id,
                            PostTradeObservationModel.id == source.post_trade_observation_id,
                        )
                    )
                    is not None
                )
                result.append(
                    EvidenceSource(
                        value.evidence.id,
                        "FT011",
                        value.evidence.created_at,
                        source.exit_review_version_id if bound else None,
                        None,
                        bound,
                        await lessons.list_version_references_for_evidence(
                            workspace_id=workspace_id, learning_evidence_id=value.evidence.id
                        ),
                    )
                )
            for row, journal_id in journals:
                result.append(
                    EvidenceSource(
                        row.id,
                        row.evidence_type,
                        row.created_at,
                        None,
                        journal_id,
                        True,
                        await lessons.list_version_references_for_evidence(
                            workspace_id=workspace_id, learning_evidence_id=row.id
                        ),
                    )
                )
            return SourceSnapshot(tuple(result), started, datetime.now(UTC))
