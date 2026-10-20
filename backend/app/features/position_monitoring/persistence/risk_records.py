"""Risk configuration and immutable snapshot persistence; no numerical decisions."""

from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.position_monitoring.domain.risk_signals import RiskParameters
from app.features.position_monitoring.persistence.models import (
    PositionRiskConfigurationModel,
    PositionRiskSnapshotModel,
)
from app.features.position_monitoring.service.risk_contracts import (
    PositionRiskView,
    RiskConfiguration,
)

RISK_VIEW = TypeAdapter(PositionRiskView)
RISK_PARAMETERS = TypeAdapter(RiskParameters)


class RiskRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def configuration(self, position_id: UUID) -> RiskConfiguration:
        row = await self._session.scalar(
            select(PositionRiskConfigurationModel)
            .where(
                PositionRiskConfigurationModel.position_id == position_id,
            )
            .order_by(PositionRiskConfigurationModel.revision.desc())
            .limit(1)
        )
        if row is None:
            return RiskConfiguration(0, False, RiskParameters())
        if row.policy_version != "POSITION_RISK_V1":
            raise ValueError("UNSUPPORTED_RISK_POLICY_VERSION")
        return RiskConfiguration(
            row.revision,
            row.enabled,
            RISK_PARAMETERS.validate_python(row.parameters),
            row.configured_at,
            row.actor,
            row.policy_version,
        )

    async def latest(self, position_id: UUID, revision: int) -> PositionRiskView | None:
        row = await self._session.scalar(
            select(PositionRiskSnapshotModel)
            .where(
                PositionRiskSnapshotModel.position_id == position_id,
                PositionRiskSnapshotModel.configuration_revision == revision,
            )
            .order_by(
                PositionRiskSnapshotModel.evaluated_at.desc(), PositionRiskSnapshotModel.id.desc()
            )
            .limit(1)
        )
        return RISK_VIEW.validate_python(row.payload) if row else None

    async def identical(self, position_id: UUID, fingerprint: str) -> PositionRiskView | None:
        row = await self._session.scalar(
            select(PositionRiskSnapshotModel).where(
                PositionRiskSnapshotModel.position_id == position_id,
                PositionRiskSnapshotModel.input_fingerprint == fingerprint,
            )
        )
        return RISK_VIEW.validate_python(row.payload) if row else None

    async def history(self, position_id: UUID) -> tuple[PositionRiskView, ...]:
        rows = (
            await self._session.scalars(
                select(PositionRiskSnapshotModel)
                .where(
                    PositionRiskSnapshotModel.position_id == position_id,
                )
                .order_by(
                    PositionRiskSnapshotModel.evaluated_at.desc(),
                    PositionRiskSnapshotModel.id.desc(),
                )
                .limit(20)
            )
        ).all()
        return tuple(RISK_VIEW.validate_python(row.payload) for row in rows)

    def add_snapshot(self, workspace_id: UUID, view: PositionRiskView) -> None:
        self._session.add(
            PositionRiskSnapshotModel(
                id=view.snapshot_id,
                workspace_id=workspace_id,
                position_id=view.position_id,
                configuration_revision=view.configuration.revision,
                input_fingerprint=view.input_fingerprint,
                evaluated_at=view.evaluated_at,
                payload=RISK_VIEW.dump_python(view, mode="json"),
            )
        )
