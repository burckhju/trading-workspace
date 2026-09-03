from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["alert_id"], ["alerts.id"], ondelete="RESTRICT", name="fk_notifications_alert"
        ),
        UniqueConstraint(
            "alert_id",
            "channel",
            "destination_key",
            name="uq_notification_alert_channel_destination",
        ),
        Index("ix_notifications_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    alert_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_key: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class NotificationDeliveryAttemptModel(Base):
    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
            name="fk_delivery_attempt_notification",
        ),
        UniqueConstraint("notification_id", "attempt_number", name="uq_delivery_attempt_number"),
        Index("ix_delivery_attempt_notification_attempted", "notification_id", "attempted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    notification_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
