"""Immutable target assessments and idempotent receipts, never execution facts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    exists,
    func,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, aliased, mapped_column

from app.database.base import Base


class HebeltraderTargetAssessmentModel(Base):
    __tablename__ = "hebeltrader_target_assessments"
    __table_args__ = (
        UniqueConstraint("previous_assessment_id", name="uq_hebeltrader_target_successor"),
        Index(
            "uq_hebeltrader_target_root",
            "workspace_id",
            "position_id",
            unique=True,
            postgresql_where=text("previous_assessment_id IS NULL"),
            sqlite_where=text("previous_assessment_id IS NULL"),
        ),
        Index("ix_hebeltrader_target_history", "workspace_id", "position_id", "recorded_at"),
        CheckConstraint("id <> previous_assessment_id", name="hebeltrader_target_not_self"),
        CheckConstraint("basis_id ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_basis"),
        CheckConstraint(
            "input_fingerprint ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_fingerprint"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    underlying_id: Mapped[UUID] = mapped_column(ForeignKey("underlyings.id", ondelete="RESTRICT"))
    source_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("external_observation_versions.id", ondelete="RESTRICT")
    )
    evidence_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("position_baseline_evidence.id", ondelete="RESTRICT")
    )
    previous_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hebeltrader_target_assessments.id", ondelete="RESTRICT")
    )
    definition_version: Mapped[str] = mapped_column(String(64))
    baseline_id: Mapped[str] = mapped_column(String(64))
    baseline_version: Mapped[str] = mapped_column(String(32))
    basis_id: Mapped[str] = mapped_column(String(64))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON())
    result: Mapped[dict[str, Any]] = mapped_column(JSON())


class HebeltraderTargetRequestModel(Base):
    __tablename__ = "hebeltrader_target_requests"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_hebeltrader_target_request"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_request_fingerprint"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("hebeltrader_target_assessments.id", ondelete="RESTRICT")
    )
    request_id: Mapped[UUID] = mapped_column(Uuid())
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())


@dataclass(frozen=True, slots=True)
class TargetAssessmentRecord:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    source_version_id: UUID | None
    evidence_revision_id: UUID | None
    previous_assessment_id: UUID | None
    definition_version: str
    baseline_id: str
    baseline_version: str
    basis_id: str
    input_fingerprint: str
    recorded_at: datetime
    recorded_by: UUID
    inputs: dict[str, Any]
    result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TargetRequestReceipt:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    assessment_id: UUID
    request_id: UUID
    request_fingerprint: str
    recorded_at: datetime
    recorded_by: UUID


def _record(row: HebeltraderTargetAssessmentModel) -> TargetAssessmentRecord:
    values = {name: getattr(row, name) for name in TargetAssessmentRecord.__dataclass_fields__}
    if row.recorded_at.utcoffset() is None:
        values["recorded_at"] = row.recorded_at.replace(tzinfo=UTC)
    return TargetAssessmentRecord(**values)


class SqlAlchemyHebeltraderTargetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> TargetAssessmentRecord | None:
        successor = aliased(HebeltraderTargetAssessmentModel)
        row = await self._session.scalar(
            select(HebeltraderTargetAssessmentModel).where(
                HebeltraderTargetAssessmentModel.workspace_id == workspace_id,
                HebeltraderTargetAssessmentModel.trade_id == trade_id,
                HebeltraderTargetAssessmentModel.position_id == position_id,
                ~exists().where(
                    successor.previous_assessment_id == HebeltraderTargetAssessmentModel.id
                ),
            )
        )
        return _record(row) if row is not None else None

    async def get(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID, assessment_id: UUID
    ) -> TargetAssessmentRecord | None:
        row = await self._session.scalar(
            select(HebeltraderTargetAssessmentModel).where(
                HebeltraderTargetAssessmentModel.id == assessment_id,
                HebeltraderTargetAssessmentModel.workspace_id == workspace_id,
                HebeltraderTargetAssessmentModel.trade_id == trade_id,
                HebeltraderTargetAssessmentModel.position_id == position_id,
            )
        )
        return _record(row) if row is not None else None

    async def count(self, workspace_id: UUID, trade_id: UUID, position_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(HebeltraderTargetAssessmentModel)
                .where(
                    HebeltraderTargetAssessmentModel.workspace_id == workspace_id,
                    HebeltraderTargetAssessmentModel.trade_id == trade_id,
                    HebeltraderTargetAssessmentModel.position_id == position_id,
                )
            )
            or 0
        )

    async def find_request(
        self, workspace_id: UUID, request_id: UUID
    ) -> TargetRequestReceipt | None:
        row = await self._session.scalar(
            select(HebeltraderTargetRequestModel).where(
                HebeltraderTargetRequestModel.workspace_id == workspace_id,
                HebeltraderTargetRequestModel.request_id == request_id,
            )
        )
        if row is None:
            return None
        values = {name: getattr(row, name) for name in TargetRequestReceipt.__dataclass_fields__}
        if row.recorded_at.utcoffset() is None:
            values["recorded_at"] = row.recorded_at.replace(tzinfo=UTC)
        return TargetRequestReceipt(**values)

    async def add(self, record: TargetAssessmentRecord) -> None:
        self._session.add(
            HebeltraderTargetAssessmentModel(
                **{name: getattr(record, name) for name in record.__dataclass_fields__}
            )
        )
        await self._session.flush()

    async def receipt(self, record: TargetRequestReceipt) -> None:
        self._session.add(
            HebeltraderTargetRequestModel(
                **{name: getattr(record, name) for name in record.__dataclass_fields__}
            )
        )
        await self._session.flush()
