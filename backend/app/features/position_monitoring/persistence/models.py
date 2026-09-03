from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
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
    triggered: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    active_alert_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
