"""Passive deadline evidence and history; no command, refresh or rule evaluation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.position_monitoring.domain.product_deadline_review import (
    ACTIVATION_SCOPE,
    RULE_SCOPE,
    RULE_VERSION,
)
from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineEpisodeModel as Episode,
)
from app.features.position_monitoring.service.product_deadline_review import (
    latest_product_deadline_assessment,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)


@dataclass(frozen=True, slots=True)
class ProductDeadlineAssessmentView:
    id: UUID
    previous_assessment_id: UUID | None
    evaluated_at: datetime
    recorded_at: datetime
    outcome: str
    reasons: tuple[str, ...]
    scheduled_at: str | None
    scheduled_on: str | None
    owner_basis_id: str
    product_evidence: dict[str, Any] | None
    calculation: dict[str, Any] | None
    qualified_b05: Literal[False] = False
    product_cutoff_status: Literal["UNVERIFIED"] = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class ProductDeadlineEpisodeView:
    id: UUID
    kind: str
    episode_number: int
    alert_id: UUID
    opening_assessment_id: UUID
    closing_assessment_id: UUID | None
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None


@dataclass(frozen=True, slots=True)
class ProductDeadlineStatusReport:
    trade_id: UUID
    position_id: UUID
    activation_status: Literal["NOT_ACTIVATED", "SCOPE_ENABLED"]
    runner_enabled: bool
    notifications_enabled: bool
    latest_assessment: ProductDeadlineAssessmentView | None
    active_episodes: tuple[ProductDeadlineEpisodeView, ...]
    recent_episodes: tuple[ProductDeadlineEpisodeView, ...]
    assessment_count: int
    episode_count: int
    read_at: datetime
    definition_version: str = RULE_VERSION
    scope: str = RULE_SCOPE
    qualified_b05: Literal[False] = False
    product_cutoff_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    full_baseline_activated: Literal[False] = False
    read_status: Literal["READ_ONLY"] = "READ_ONLY"


def _assessment_view(row: Assessment) -> ProductDeadlineAssessmentView:
    return ProductDeadlineAssessmentView(
        row.id,
        row.previous_assessment_id,
        row.evaluated_at,
        row.recorded_at,
        row.outcome,
        tuple(row.result["reasons"]),
        row.result["scheduled_at"],
        row.result.get("scheduled_on"),
        row.owner_basis_id,
        row.inputs.get("product_evidence"),
        row.result["calculation"],
    )


def _episode_view(row: Episode) -> ProductDeadlineEpisodeView:
    return ProductDeadlineEpisodeView(
        **{key: getattr(row, key) for key in ProductDeadlineEpisodeView.__dataclass_fields__}
    )


class ProductDeadlineReviewReader:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        scope: str = "DISABLED",
        runner_enabled: bool = False,
        notifications_enabled: bool = False,
    ) -> None:
        self._engine = engine
        self._scope = scope
        self._runner_enabled = runner_enabled
        self._notifications_enabled = notifications_enabled

    async def read(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> ProductDeadlineStatusReport:
        now = datetime.now(UTC)
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                trade = await SqlAlchemyReadOnlyTradeRepository(session).get(workspace_id, trade_id)
                position = await SqlAlchemyPositionRepository(session).get_for_trade(
                    workspace_id, trade_id
                )
                if trade is None or position is None or position.id != position_id:
                    raise ApplicationError(
                        code="PRODUCT_DEADLINE_POSITION_NOT_FOUND",
                        message="Position nicht gefunden.",
                        status_code=404,
                    )
                latest = await latest_product_deadline_assessment(
                    session, workspace_id, position_id
                )
                scope = (
                    Episode.workspace_id == workspace_id,
                    Episode.position_id == position_id,
                    Episode.rule_version == RULE_VERSION,
                )
                recent = tuple(
                    await session.scalars(
                        select(Episode)
                        .where(*scope)
                        .order_by(Episode.opened_at.desc(), Episode.id.desc())
                        .limit(50)
                    )
                )
                active = tuple(
                    await session.scalars(
                        select(Episode)
                        .where(*scope, Episode.closed_at.is_(None))
                        .order_by(Episode.kind)
                    )
                )
                assessments = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(Assessment)
                        .where(
                            Assessment.workspace_id == workspace_id,
                            Assessment.position_id == position_id,
                            Assessment.rule_version == RULE_VERSION,
                        )
                    )
                    or 0
                )
                episodes = int(
                    await session.scalar(select(func.count()).select_from(Episode).where(*scope))
                    or 0
                )
                enabled = self._scope == ACTIVATION_SCOPE
                return ProductDeadlineStatusReport(
                    trade_id,
                    position_id,
                    "SCOPE_ENABLED" if enabled else "NOT_ACTIVATED",
                    self._runner_enabled and enabled,
                    self._notifications_enabled and enabled,
                    _assessment_view(latest) if latest else None,
                    tuple(_episode_view(row) for row in active),
                    tuple(_episode_view(row) for row in recent),
                    assessments,
                    episodes,
                    now,
                )
            finally:
                await session.rollback()
