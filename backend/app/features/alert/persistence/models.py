from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AlertModel(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["position_id"], ["positions.id"], ondelete="RESTRICT", name="fk_alerts_position"
        ),
        ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="RESTRICT", name="fk_alerts_trade"
        ),
        Index("ix_alerts_position_status_detected", "position_id", "status", "detected_at"),
        Index("ix_alerts_trade_detected", "trade_id", "detected_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    position_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    observed_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    market_data_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
