"""An independent, price-free deadline sweep for the explicitly enabled V2 scope."""

import logging
from dataclasses import dataclass

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.position_monitoring.domain.product_deadline_review import (
    ACTIVATION_SCOPE,
    RULE_VERSION,
)
from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineEpisodeModel,
)
from app.features.position_monitoring.service.product_deadline_review import (
    ProductDeadlineReviewService,
)
from app.features.trade_position.service.open_position_reader import OpenPositionReader

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProductDeadlineRunResult:
    positions_evaluated: int = 0
    alerts_created: int = 0
    notifications_created: int = 0
    data_problems: int = 0
    position_errors: int = 0


class ProductDeadlineReviewRuntime:
    def __init__(
        self,
        database: DatabaseManager,
        *,
        scope: str = "DISABLED",
        notifications_enabled: bool = False,
    ) -> None:
        self._database = database
        self._scope = scope
        self._notifications_enabled = notifications_enabled

    async def run(self) -> ProductDeadlineRunResult:
        if self._scope != ACTIVATION_SCOPE:
            return ProductDeadlineRunResult()
        async with self._database.session_context() as session:
            positions = await OpenPositionReader(session).list_open()
            subjects = {(p.workspace_id, p.trade_id, p.position_id) for p in positions}
            active = (
                await session.execute(
                    select(
                        ProductDeadlineEpisodeModel.workspace_id,
                        ProductDeadlineEpisodeModel.trade_id,
                        ProductDeadlineEpisodeModel.position_id,
                    ).where(
                        ProductDeadlineEpisodeModel.rule_version == RULE_VERSION,
                        ProductDeadlineEpisodeModel.closed_at.is_(None),
                    )
                )
            ).all()
            subjects.update((row.workspace_id, row.trade_id, row.position_id) for row in active)
        evaluated = alerts = notifications = problems = errors = 0
        for workspace_id, trade_id, position_id in sorted(subjects):
            try:
                async with self._database.session_context() as session:
                    result = await ProductDeadlineReviewService(session).evaluate(
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=position_id,
                        notifications_enabled=self._notifications_enabled,
                    )
                evaluated += 1
                alerts += result.alerts_created
                notifications += result.notifications_created
                problems += int(result.data_problem_active)
            except Exception:
                errors += 1
                logger.exception(
                    "product_deadline_review_evaluation_failed",
                    extra={"position_id": str(position_id)},
                )
        return ProductDeadlineRunResult(evaluated, alerts, notifications, problems, errors)
