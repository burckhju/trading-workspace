"""B04 sweep attached to the existing runner; activation is global and explicit."""

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossEpisodeModel,
)
from app.features.position_monitoring.service.hebeltrader_b58_sources import B58SourceRegistry
from app.features.position_monitoring.service.hebeltrader_loss import HebeltraderLossService
from app.features.position_monitoring.service.rule_prices import ProductValuationReader
from app.features.trade_position.service.open_position_reader import OpenPositionReader

logger = logging.getLogger(__name__)
ActivationScope = Literal["DISABLED", "B04_B57_V1"]


@dataclass(frozen=True, slots=True)
class LossRunResult:
    positions_evaluated: int = 0
    alerts_created: int = 0
    notifications_created: int = 0
    data_problems: int = 0
    position_errors: int = 0


class HebeltraderLossRuntime:
    def __init__(
        self,
        database: DatabaseManager,
        *,
        scope: ActivationScope = "DISABLED",
        products: ProductValuationReader | None = None,
        notifications_enabled: bool = False,
        sources: B58SourceRegistry | None = None,
    ) -> None:
        self._database = database
        self._scope = scope
        self._products = products
        self._notifications_enabled = notifications_enabled
        self._sources = sources or B58SourceRegistry()

    async def run(self) -> LossRunResult:
        if self._scope != "B04_B57_V1":
            return LossRunResult()
        async with self._database.session_context() as session:
            open_positions = await OpenPositionReader(session).list_open()
            subjects = {(p.workspace_id, p.trade_id, p.position_id) for p in open_positions}
            # A full sale removes an open position; its active episode must still
            # be visited to terminate pending notices without losing history.
            active = (
                await session.execute(
                    select(
                        HebeltraderLossEpisodeModel.workspace_id,
                        HebeltraderLossEpisodeModel.trade_id,
                        HebeltraderLossEpisodeModel.position_id,
                    ).where(HebeltraderLossEpisodeModel.closed_at.is_(None))
                )
            ).all()
            subjects.update((row.workspace_id, row.trade_id, row.position_id) for row in active)
        open_ids = {p.position_id for p in open_positions}
        evaluated = alerts = notifications = problems = errors = 0
        for workspace_id, trade_id, position_id in sorted(subjects):
            if position_id in open_ids and self._products is not None:
                try:
                    # Existing source selection, provider budget, caches and
                    # retention perform acquisition outside the economic lock.
                    await self._products.for_trade(trade_id)
                except Exception:
                    logger.exception(
                        "b04_quote_refresh_failed", extra={"position_id": str(position_id)}
                    )
                    # Persisted status gaps/unknown supply are assessed below;
                    # a transport failure is never translated into CLOSED.
            try:
                async with self._database.session_context() as session:
                    result = await HebeltraderLossService(session, sources=self._sources).evaluate(
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=position_id,
                        notifications_enabled=self._notifications_enabled,
                    )
                evaluated += 1
                alerts += int(result.alert_created)
                notifications += int(result.notification_created)
                problems += int(result.outcome == "NOT_ASSESSABLE")
            except Exception:
                errors += 1
                logger.exception("b04_evaluation_failed", extra={"position_id": str(position_id)})
        return LossRunResult(evaluated, alerts, notifications, problems, errors)
