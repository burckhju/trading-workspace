from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MonitoringRuleStateModel(Base):
    __tablename__ = "monitoring_rule_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            ondelete="CASCADE",
            name="fk_monitoring_rule_states_position",
        ),
        ForeignKeyConstraint(
            ["active_alert_id"],
            ["alerts.id"],
            ondelete="SET NULL",
            name="fk_monitoring_rule_states_active_alert",
        ),
        UniqueConstraint("position_id", "rule_key", name="uq_monitoring_rule_state_position_rule"),
        Index("ix_monitoring_rule_states_triggered", "triggered", "last_seen_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    position_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(200), nullable=False)
    price_binding_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    triggered: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_basis: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="SOURCE_TIMESTAMP",
        server_default="SOURCE_TIMESTAMP",
    )
    last_observed_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    active_alert_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class PositionRiskConfigurationModel(Base):
    """Append-only per-position configuration; absence means disabled preview."""

    __tablename__ = "position_risk_configurations"
    __table_args__ = (
        UniqueConstraint("position_id", "revision", name="uq_position_risk_configuration_revision"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    configured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class PositionRiskSnapshotModel(Base):
    """Immutable evaluated inputs, state and result; corrections create new records."""

    __tablename__ = "position_risk_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "position_id", "input_fingerprint", name="uq_position_risk_snapshot_input"
        ),
        Index("ix_position_risk_snapshot_position_time", "position_id", "evaluated_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    configuration_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
