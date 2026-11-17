"""Read-only visibility of partial scope, last assessment and persistent episode."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.position_monitoring.domain.hebeltrader_loss import (
    BASELINE_ID,
    BASELINE_VERSION,
    MISSING_RULES,
    RULE_SCOPE,
    RULE_VERSION,
)
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossEpisodeModel as Episode,
)
from app.features.position_monitoring.service.hebeltrader_b58_sources import B58SourceRegistry
from app.features.position_monitoring.service.hebeltrader_loss import latest_assessment
from app.features.position_monitoring.service.hebeltrader_loss_runtime import ActivationScope
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)


@dataclass(frozen=True, slots=True)
class LossAssessmentView:
    id: UUID
    evaluated_at: datetime
    recorded_at: datetime
    outcome: str
    reasons: tuple[str, ...]
    bid_at: datetime | None
    bid: str | None
    gross_entry: str
    currency: str | None
    remaining_quantity: int
    completed_sessions_at_bid: int | None
    owner_basis_id: str


@dataclass(frozen=True, slots=True)
class LossEpisodeView:
    id: UUID
    episode_number: int
    alert_id: UUID
    opening_assessment_id: UUID
    closing_assessment_id: UUID | None
    opened_at: datetime
    closed_at: datetime | None
    close_reason: str | None


@dataclass(frozen=True, slots=True)
class LossStatusReport:
    trade_id: UUID
    position_id: UUID
    activation_status: Literal["NOT_ACTIVATED", "BLOCKED_SOURCE", "SCOPE_ENABLED"]
    runner_enabled: bool
    source_qualification_references: tuple[str, ...]
    latest_assessment: LossAssessmentView | None
    active_episode: LossEpisodeView | None
    recent_episodes: tuple[LossEpisodeView, ...]
    assessment_count: int
    episode_count: int
    read_at: datetime
    definition_version: str = RULE_VERSION
    rule_scope: str = RULE_SCOPE
    baseline_id: str = BASELINE_ID
    baseline_version: str = BASELINE_VERSION
    implementation_status: Literal["B04_B57_IMPLEMENTED"] = "B04_B57_IMPLEMENTED"
    full_baseline_activated: Literal[False] = False
    remaining_scope: tuple[str, ...] = MISSING_RULES
    read_status: Literal["READ_ONLY"] = "READ_ONLY"


def assessment_view(row: Assessment) -> LossAssessmentView:
    result = row.result
    return LossAssessmentView(
        row.id,
        row.evaluated_at,
        row.recorded_at,
        row.outcome,
        tuple(result["reasons"]),
        row.bid_at,
        result["bid"],
        result["gross_entry"],
        row.inputs["economic_basis"]["cost_basis_currency"],
        result["remaining_quantity"],
        result["completed_sessions_at_bid"],
        row.owner_basis_id,
    )


def episode_view(row: Episode) -> LossEpisodeView:
    return LossEpisodeView(
        **{key: getattr(row, key) for key in LossEpisodeView.__dataclass_fields__}
    )


class HebeltraderLossReader:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        scope: ActivationScope = "DISABLED",
        runner_enabled: bool = False,
        sources: B58SourceRegistry | None = None,
    ) -> None:
        self._engine = engine
        self._scope = scope
        self._runner_enabled = runner_enabled
        self._sources = sources or B58SourceRegistry()

    async def read(self, workspace_id: UUID, trade_id: UUID, position_id: UUID) -> LossStatusReport:
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
                        code="B04_POSITION_NOT_FOUND",
                        message="Position nicht gefunden.",
                        status_code=404,
                    )
                latest = await latest_assessment(session, workspace_id, position_id)
                scope: tuple[Any, ...] = (
                    Episode.workspace_id == workspace_id,
                    Episode.position_id == position_id,
                    Episode.rule_version == RULE_VERSION,
                )
                episodes = tuple(
                    (
                        await session.scalars(
                            select(Episode)
                            .where(*scope)
                            .order_by(Episode.episode_number.desc())
                            .limit(50)
                        )
                    ).all()
                )
                active = next((item for item in episodes if item.closed_at is None), None)
                assessment_count = int(
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
                episode_count = int(
                    await session.scalar(select(func.count()).select_from(Episode).where(*scope))
                    or 0
                )
                references = self._sources.qualification_references
                return LossStatusReport(
                    trade_id,
                    position_id,
                    (
                        "NOT_ACTIVATED"
                        if self._scope == "DISABLED"
                        else "SCOPE_ENABLED" if references else "BLOCKED_SOURCE"
                    ),
                    self._runner_enabled,
                    references,
                    assessment_view(latest) if latest else None,
                    episode_view(active) if active else None,
                    tuple(episode_view(item) for item in episodes),
                    assessment_count,
                    episode_count,
                    now,
                )
            finally:
                await session.rollback()
