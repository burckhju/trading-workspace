"""Independent, append-only assessments and deduplicated product-date notices."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductDeadlineAssessmentModel(Base):
    __tablename__ = "product_deadline_assessments"
    __table_args__ = (
        UniqueConstraint("previous_assessment_id", name="uq_product_deadline_successor"),
        Index(
            "uq_product_deadline_root",
            "workspace_id",
            "position_id",
            "rule_version",
            unique=True,
            postgresql_where=text("previous_assessment_id IS NULL"),
            sqlite_where=text("previous_assessment_id IS NULL"),
        ),
        Index("ix_product_deadline_history", "workspace_id", "position_id", "recorded_at"),
        CheckConstraint(
            "outcome IN ('BEFORE_WARNING','WARNING_DUE','EXIT_SESSION_STARTED',"
            "'CALENDAR_SESSION_ENDED','WARNING_DAY_REACHED','DEADLINE_DAY_REACHED',"
            "'DEADLINE_DAY_PASSED','UNAVAILABLE','CLOSED')",
            name="product_deadline_outcome",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    rule_version: Mapped[str] = mapped_column(String(64))
    previous_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT")
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    owner_basis_id: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(32))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON())
    result: Mapped[dict[str, Any]] = mapped_column(JSON())


class ProductDeadlineEpisodeModel(Base):
    __tablename__ = "product_deadline_episodes"
    __table_args__ = (
        UniqueConstraint(
            "opening_assessment_id", "kind", name="uq_product_deadline_episode_opening"
        ),
        UniqueConstraint("alert_id", name="uq_product_deadline_episode_alert"),
        UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "event_key",
            name="uq_product_deadline_event",
        ),
        UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "episode_number",
            name="uq_product_deadline_episode_number",
        ),
        Index(
            "uq_product_deadline_active",
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
            sqlite_where=text("closed_at IS NULL"),
        ),
        CheckConstraint("episode_number > 0", name="product_deadline_episode_positive"),
        CheckConstraint(
            "kind IN ('DEADLINE_REVIEW','DATA_UNAVAILABLE')", name="product_deadline_kind"
        ),
        CheckConstraint(
            "(kind = 'DEADLINE_REVIEW' AND event_key IS NOT NULL) OR "
            "(kind = 'DATA_UNAVAILABLE' AND event_key IS NULL)",
            name="product_deadline_event_shape",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    rule_version: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32))
    event_key: Mapped[str | None] = mapped_column(String(64))
    episode_number: Mapped[int] = mapped_column(Integer())
    opening_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT")
    )
    closing_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT")
    )
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alerts.id", ondelete="RESTRICT"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(100))
