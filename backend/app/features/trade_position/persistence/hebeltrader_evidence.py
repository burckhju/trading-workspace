"""Immutable evidence revisions; economic executions stay with their existing owner."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.trade_position.domain.hebeltrader_evidence import (
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
)

DECLARATION = TypeAdapter(HebeltraderEvidenceDeclaration)


class HebeltraderEvidenceModel(Base):
    __tablename__ = "position_baseline_evidence"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_position_baseline_request"),
        UniqueConstraint("supersedes_evidence_id", name="uq_position_baseline_successor"),
        Index(
            "uq_position_baseline_root",
            "workspace_id",
            "position_id",
            unique=True,
            postgresql_where=text("supersedes_evidence_id IS NULL"),
            sqlite_where=text("supersedes_evidence_id IS NULL"),
        ),
        Index("ix_position_baseline_history", "workspace_id", "position_id", "recorded_at"),
        CheckConstraint("id <> supersedes_evidence_id", name="baseline_evidence_not_self"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="baseline_evidence_fingerprint"
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
    declaration: Mapped[dict[str, Any]] = mapped_column(JSON())
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())
    request_id: Mapped[UUID] = mapped_column(Uuid())
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    supersedes_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("position_baseline_evidence.id", ondelete="RESTRICT")
    )


class HebeltraderExecutionReferenceModel(Base):
    """Trigger-derived deletion protection, never an independent execution fact."""

    __tablename__ = "position_baseline_execution_refs"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ENTRY_BUY','UNDERLYING_BUY','Z1_SELL')", name="baseline_execution_role"
        ),
    )
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("position_baseline_evidence.id", ondelete="RESTRICT"), primary_key=True
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_records.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), primary_key=True)


def to_domain(row: HebeltraderEvidenceModel) -> HebeltraderEvidenceRevision:
    declaration = DECLARATION.validate_python(row.declaration)
    if declaration.source_version_id != row.source_version_id:
        raise ValueError("Evidence source reference disagrees with its immutable declaration")
    return HebeltraderEvidenceRevision(
        id=row.id,
        workspace_id=row.workspace_id,
        trade_id=row.trade_id,
        position_id=row.position_id,
        product_id=row.product_id,
        underlying_id=row.underlying_id,
        declaration=declaration,
        recorded_at=(
            row.recorded_at.replace(tzinfo=UTC)
            if row.recorded_at.utcoffset() is None
            else row.recorded_at
        ),
        recorded_by=row.recorded_by,
        request_id=row.request_id,
        request_fingerprint=row.request_fingerprint,
        supersedes_evidence_id=row.supersedes_evidence_id,
    )


class SqlAlchemyHebeltraderEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, revision: HebeltraderEvidenceRevision) -> None:
        self._session.add(
            HebeltraderEvidenceModel(
                **{
                    name: getattr(revision, name)
                    for name in HebeltraderEvidenceRevision.__dataclass_fields__
                    if name != "declaration"
                },
                source_version_id=revision.declaration.source_version_id,
                declaration=DECLARATION.dump_python(revision.declaration, mode="json"),
            )
        )
        # The transaction owner holds the trade lock and decides whether to commit.
        # PostgreSQL populates protected reference rows in this same transaction.
        await self._session.flush()

    async def find_request(
        self, workspace_id: UUID, request_id: UUID
    ) -> HebeltraderEvidenceRevision | None:
        row = await self._session.scalar(
            select(HebeltraderEvidenceModel).where(
                HebeltraderEvidenceModel.workspace_id == workspace_id,
                HebeltraderEvidenceModel.request_id == request_id,
            )
        )
        return None if row is None else to_domain(row)

    async def history(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> tuple[HebeltraderEvidenceRevision, ...]:
        rows = tuple(
            await self._session.scalars(
                select(HebeltraderEvidenceModel)
                .where(
                    HebeltraderEvidenceModel.workspace_id == workspace_id,
                    HebeltraderEvidenceModel.trade_id == trade_id,
                    HebeltraderEvidenceModel.position_id == position_id,
                )
                .order_by(HebeltraderEvidenceModel.recorded_at, HebeltraderEvidenceModel.id)
            )
        )
        # Equal recording clocks are valid. The predecessor determines revision
        # chronology then; random UUID order must never select an older revision.
        successors = {row.supersedes_evidence_id: row for row in rows}
        ordered: list[HebeltraderEvidenceRevision] = []
        predecessor: UUID | None = None
        while predecessor in successors and len(ordered) < len(rows):
            row = successors[predecessor]
            ordered.append(to_domain(row))
            predecessor = row.id
        if len(ordered) != len(rows) or len(successors) != len(rows):
            raise ValueError("Evidence revision chain is incomplete or ambiguous")
        return tuple(ordered)
