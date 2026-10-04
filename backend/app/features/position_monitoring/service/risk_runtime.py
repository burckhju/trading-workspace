"""Bounded, persisted-input risk sweep; notification delivery remains with its owner."""

import logging
from datetime import UTC, datetime

from app.database import DatabaseManager
from app.features.position_monitoring.service.cycle import CreatedPositionAlert
from app.features.position_monitoring.service.risk import PositionRiskService
from app.features.trade_position.service.open_position_reader import OpenPositionReader

logger = logging.getLogger(__name__)


class RiskRuntimeService:
    def __init__(self, database: DatabaseManager) -> None:
        self._database = database

    async def run(self) -> tuple[CreatedPositionAlert, ...]:
        async with self._database.session_context() as session:
            positions = await OpenPositionReader(session).list_open()
        result: list[CreatedPositionAlert] = []
        now = datetime.now(UTC)
        for position in positions:
            try:
                async with self._database.session_context() as session:
                    _, alerts = await PositionRiskService(session).evaluate(
                        workspace_id=position.workspace_id,
                        trade_id=position.trade_id,
                        now=now,
                    )
                    result.extend(alerts)
            except Exception:
                logger.exception(
                    "position_risk_evaluation_failed",
                    extra={"position_id": str(position.position_id)},
                )
        return tuple(result)
