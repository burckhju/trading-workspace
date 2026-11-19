"""Independent global review sweep attached to the existing background runner."""

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.position_monitoring.domain.indicative_policy import (
    REVIEW_FAMILY_VERSIONS,
    ReviewActivationScope,
    review_policy,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryEpisodeModel,
)
from app.features.position_monitoring.service.indicative_entry import (
    IndicativeEntryService,
)
from app.features.position_monitoring.service.rule_prices import ProductValuationReader
from app.features.trade_position.service.open_position_reader import OpenPositionReader

logger = logging.getLogger(__name__)


class IndicativeReadiness(Protocol):
    async def prepare_for_review(
        self, *, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class IndicativeRunResult:
    positions_evaluated: int = 0
    alerts_created: int = 0
    notifications_created: int = 0
    data_problems: int = 0
    position_errors: int = 0


class IndicativeEntryRuntime:
    def __init__(
        self,
        database: DatabaseManager,
        *,
        scope: ReviewActivationScope = "DISABLED",
        products: ProductValuationReader | None = None,
        notifications_enabled: bool = False,
        readiness: IndicativeReadiness | None = None,
    ) -> None:
        self._database = database
        self._scope = scope
        self._policy = review_policy(scope)
        self._products = products
        self._notifications_enabled = notifications_enabled
        self._readiness = readiness

    async def run(self) -> IndicativeRunResult:
        if self._scope == "DISABLED":
            return IndicativeRunResult()
        async with self._database.session_context() as session:
            positions = await OpenPositionReader(session).list_open()
            subjects = {(p.workspace_id, p.trade_id, p.position_id) for p in positions}
            active = (
                await session.execute(
                    select(
                        IndicativeEntryEpisodeModel.workspace_id,
                        IndicativeEntryEpisodeModel.trade_id,
                        IndicativeEntryEpisodeModel.position_id,
                    ).where(
                        IndicativeEntryEpisodeModel.closed_at.is_(None),
                        IndicativeEntryEpisodeModel.rule_version.in_(REVIEW_FAMILY_VERSIONS),
                    )
                )
            ).all()
            subjects.update((row.workspace_id, row.trade_id, row.position_id) for row in active)
        open_ids = {p.position_id for p in positions}
        evaluated = alerts = notifications = problems = errors = 0
        for workspace_id, trade_id, position_id in sorted(subjects):
            refresh_failed = False
            if (
                position_id in open_ids
                and self._policy.allow_assumed_product_history
                and self._readiness is not None
            ):
                try:
                    await self._readiness.prepare_for_review(
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=position_id,
                    )
                except Exception:
                    logger.exception(
                        "indicative_input_preparation_failed",
                        extra={"position_id": str(position_id)},
                    )
            if position_id in open_ids and self._products is not None:
                try:
                    # Existing acquisition/selection/retention owns all network
                    # work, outside the economic lock and with shared budgets.
                    value = await self._products.for_trade(trade_id)
                    refresh_failed = value is None or bool(value.quote_refresh_error)
                except Exception:
                    refresh_failed = True
                    logger.exception(
                        "indicative_quote_refresh_failed",
                        extra={"position_id": str(position_id)},
                    )
            try:
                async with self._database.session_context() as session:
                    result = await IndicativeEntryService(session, policy=self._policy).evaluate(
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=position_id,
                        notifications_enabled=self._notifications_enabled,
                        refresh_failed=refresh_failed,
                    )
                evaluated += 1
                alerts += result.alerts_created
                notifications += result.notifications_created
                problems += int(result.data_problem_active)
            except Exception:
                errors += 1
                logger.exception(
                    "indicative_entry_evaluation_failed",
                    extra={"position_id": str(position_id)},
                )
        return IndicativeRunResult(evaluated, alerts, notifications, problems, errors)
