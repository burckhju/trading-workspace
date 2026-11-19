from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AlertModel(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('STOP_REACHED', 'TARGET_REACHED', 'RISK_TREND_CHANGED', "
            "'RISK_VOLATILITY_HIGH', 'HEBELTRADER_B04_LOSS', 'INDICATIVE_ENTRY_LOSS', "
            "'POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE', 'PRODUCT_DEADLINE_REVIEW')",
            name="alert_type_valid",
        ),
        CheckConstraint(
            "(alert_type IN ('POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE', "
            "'PRODUCT_DEADLINE_REVIEW') "
            "AND observed_value IS NULL AND threshold_value IS NULL) OR "
            "(alert_type NOT IN ('POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE', "
            "'PRODUCT_DEADLINE_REVIEW') "
            "AND observed_value IS NOT NULL AND threshold_value IS NOT NULL)",
            name="alert_value_shape",
        ),
        CheckConstraint("status IN ('OPEN', 'RESOLVED', 'INVALIDATED')", name="alert_status_valid"),
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
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    market_data_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    price_context: Mapped[dict[str, str | None] | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
