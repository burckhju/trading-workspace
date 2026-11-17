"""Monitoring-owned assessment ledger and durable loss episodes."""

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


class HebeltraderLossAssessmentModel(Base):
    __tablename__ = "hebeltrader_loss_assessments"
    __table_args__ = (
        UniqueConstraint("previous_assessment_id", name="uq_hebeltrader_loss_successor"),
        Index(
            "uq_hebeltrader_loss_root",
            "workspace_id",
            "position_id",
            "rule_version",
            unique=True,
            postgresql_where=text("previous_assessment_id IS NULL"),
            sqlite_where=text("previous_assessment_id IS NULL"),
        ),
        Index("ix_hebeltrader_loss_history", "workspace_id", "position_id", "recorded_at"),
        CheckConstraint(
            "outcome IN ('LOSS','RECOVERED','NOT_ASSESSABLE','NOT_REACHED','CLOSED')",
            name="hebeltrader_loss_outcome",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    rule_version: Mapped[str] = mapped_column(String(64))
    previous_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT")
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    owner_basis_id: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(32))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON())
    result: Mapped[dict[str, Any]] = mapped_column(JSON())


class HebeltraderLossEpisodeModel(Base):
    __tablename__ = "hebeltrader_loss_episodes"
    __table_args__ = (
        UniqueConstraint("opening_assessment_id", name="uq_hebeltrader_loss_episode_opening"),
        UniqueConstraint("alert_id", name="uq_hebeltrader_loss_episode_alert"),
        UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "episode_number",
            name="uq_hebeltrader_loss_episode_number",
        ),
        Index(
            "uq_hebeltrader_loss_active",
            "workspace_id",
            "position_id",
            "rule_version",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
            sqlite_where=text("closed_at IS NULL"),
        ),
        CheckConstraint("episode_number > 0", name="hebeltrader_loss_episode_positive"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    rule_version: Mapped[str] = mapped_column(String(64))
    episode_number: Mapped[int] = mapped_column(Integer())
    opening_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT")
    )
    closing_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT")
    )
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alerts.id", ondelete="RESTRICT"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(100))
