"""Passive visibility of review assessments and episodes; no refresh or commands."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.position_monitoring.domain.indicative_entry import (
    RULE_SCOPE,
    RULE_VERSION,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryEpisodeModel as Episode,
)
from app.features.position_monitoring.service.indicative_entry import (
    latest_indicative_assessment,
)
from app.features.position_monitoring.service.indicative_entry_inputs import (
    status_point_context,
)
from app.features.position_monitoring.service.indicative_entry_runtime import (
    ReviewActivationScope,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)


@dataclass(frozen=True, slots=True)
class IndicativeAssessmentView:
    id: UUID
    evaluated_at: datetime
    recorded_at: datetime
    outcome: str
    reasons: tuple[str, ...]
    evaluation_mode: str | None
    bid: str | None
    gross_entry: str
    currency: str | None
    remaining_quantity: int
    original_bid_at: str | None
    received_at: str | None
    completed_sessions: int | None
    session_count_at: str
    review_completed_sessions: int | None
    review_due: bool | None
    owner_basis_id: str
    source: dict[str, str | None]


@dataclass(frozen=True, slots=True)
class IndicativeEpisodeView:
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
class IndicativeStatusReport:
    trade_id: UUID
    position_id: UUID
    activation_status: Literal["NOT_ACTIVATED", "SCOPE_ENABLED"]
    runner_enabled: bool
    notifications_enabled: bool
    latest_assessment: IndicativeAssessmentView | None
    active_episodes: tuple[IndicativeEpisodeView, ...]
    recent_episodes: tuple[IndicativeEpisodeView, ...]
    assessment_count: int
    episode_count: int
    read_at: datetime
    definition_version: str = RULE_VERSION
    scope: str = RULE_SCOPE
    qualified_b04: Literal[False] = False
    full_baseline_activated: Literal[False] = False
    read_status: Literal["READ_ONLY"] = "READ_ONLY"


def _assessment_view(row: Assessment) -> IndicativeAssessmentView:
    result = row.result
    saved = row.inputs.get("saved_quote") or {}
    route = saved.get("route") or {}
    return IndicativeAssessmentView(
        row.id,
        row.evaluated_at,
        row.recorded_at,
        row.outcome,
        tuple(result["reasons"]),
        result["evaluation_mode"],
        result["bid"],
        result["gross_entry"],
        row.inputs["economic_basis"]["cost_basis_currency"],
        result["remaining_quantity"],
        result["original_bid_at"],
        result["received_at"],
        result["completed_sessions"],
        result["session_count_at"],
        result["review_completed_sessions"],
        result["review_due"],
        row.owner_basis_id,
        {
            "provider": saved.get("provider"),
            "listing_id": route.get("warrant_listing_id"),
            "identity_key": route.get("identity_key"),
            **status_point_context(row.inputs),
        },
    )


def _episode_view(row: Episode) -> IndicativeEpisodeView:
    return IndicativeEpisodeView(
        **{key: getattr(row, key) for key in IndicativeEpisodeView.__dataclass_fields__}
    )


class IndicativeEntryReader:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        scope: ReviewActivationScope = "DISABLED",
        runner_enabled: bool = False,
        notifications_enabled: bool = False,
    ) -> None:
        self._engine = engine
        self._scope = scope
        self._runner_enabled = runner_enabled
        self._notifications_enabled = notifications_enabled

    async def read(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> IndicativeStatusReport:
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
                        code="REVIEW_POSITION_NOT_FOUND",
                        message="Position nicht gefunden.",
                        status_code=404,
                    )
                latest = await latest_indicative_assessment(session, workspace_id, position_id)
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
                # An old active reminder must not disappear behind many newer
                # data episodes just because the bounded history is truncated.
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
                return IndicativeStatusReport(
                    trade_id,
                    position_id,
                    "NOT_ACTIVATED" if self._scope == "DISABLED" else "SCOPE_ENABLED",
                    self._runner_enabled,
                    self._notifications_enabled,
                    _assessment_view(latest) if latest else None,
                    tuple(_episode_view(row) for row in active),
                    tuple(_episode_view(row) for row in recent),
                    assessments,
                    episodes,
                    now,
                )
            finally:
                await session.rollback()
