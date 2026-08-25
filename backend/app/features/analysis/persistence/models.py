"""SQLAlchemy persistence models for immutable analysis versions."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.database.base import Base
from app.features.analysis.domain.governed_provenance import governed_baseline_definition
from app.features.model.persistence.models import GovernedModelRecord, ModelVersionRecord


class MarketAnalysisModel(Base):
    __tablename__ = "market_analyses"
    __table_args__ = (Index("ix_market_analyses_workspace_created", "workspace_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False
    )
    listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class MarketAnalysisRunModel(Base):
    __tablename__ = "market_analysis_runs"
    __table_args__ = (
        UniqueConstraint("analysis_id", "version", name="uq_market_analysis_runs_analysis_version"),
        Index("ix_market_analysis_runs_governed_model_version", "governed_model_version_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_analyses.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    governed_model_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("governed_model_versions.id", ondelete="RESTRICT"), nullable=True
    )
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, str | None]] = mapped_column(JSON, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    data_sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)


class MarketAnalysisSnapshotRowModel(Base):
    __tablename__ = "market_analysis_snapshot_rows"
    __table_args__ = (
        UniqueConstraint("run_id", "trading_date", name="uq_market_analysis_snapshot_run_date"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 6))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(20), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class MarketAnalysisCriterionModel(Base):
    __tablename__ = "market_analysis_criterion_results"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    classification: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class MarketAnalysisEventModel(Base):
    """Append-only lifecycle event; terminal run rows remain immutable."""

    __tablename__ = "market_analysis_events"
    __table_args__ = (
        Index("ix_market_analysis_events_analysis_occurred", "analysis_id", "occurred_at"),
        UniqueConstraint(
            "analysis_id",
            "version",
            "event_type",
            name="uq_market_analysis_events_version_type",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_analyses.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE")
    )
    version: Mapped[int | None] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    source_version: Mapped[int | None] = mapped_column(Integer)
    replacement_version: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


@event.listens_for(MarketAnalysisRunModel, "before_insert")
def attach_governed_model_provenance(
    _mapper: Mapper[MarketAnalysisRunModel],
    connection: Connection,
    target: MarketAnalysisRunModel,
) -> None:
    """Attach an exact approved legacy baseline when one exists.

    This is intentionally not activation.  Runtime behavior still comes from
    the released code identified by ``model_id``/``model_version``.  The
    governed reference is written only when exactly one APPROVED ModelVersion
    declares the matching immutable runtime contract.  Missing or ambiguous
    governance therefore results in NULL provenance rather than a false link.
    """
    if (
        target.governed_model_version_id is not None
        or connection.dialect.name != "postgresql"
    ):
        return

    workspace_id = connection.execute(
        select(MarketAnalysisModel.workspace_id).where(
            MarketAnalysisModel.id == target.analysis_id
        )
    ).scalar_one_or_none()
    if workspace_id is None:
        return

    expected = governed_baseline_definition()
    definition = ModelVersionRecord.definition
    candidates = tuple(
        connection.execute(
            select(ModelVersionRecord.id)
            .join(GovernedModelRecord, GovernedModelRecord.id == ModelVersionRecord.model_id)
            .where(
                GovernedModelRecord.workspace_id == workspace_id,
                GovernedModelRecord.model_key == target.model_id,
                ModelVersionRecord.status == "APPROVED",
                definition["runtime_contract"].astext == expected["runtime_contract"],
                definition["runtime_model_id"].astext == target.model_id,
                definition["runtime_model_version"].astext == target.model_version,
                definition["implementation_ref"].astext == expected["implementation_ref"],
                definition["rule_representation"].astext == expected["rule_representation"],
            )
        ).scalars()
    )
    if len(candidates) == 1:
        target.governed_model_version_id = candidates[0]
