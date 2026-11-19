"""Separate review ledger and episodes; no references to strict B04 state."""

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

FAMILY_FILTER = "rule_version IN ('indicative-entry-review-v1','indicative-entry-review-v2')"


class IndicativeEntryAssessmentModel(Base):
    __tablename__ = "indicative_entry_assessments"
    __table_args__ = (
        UniqueConstraint("previous_assessment_id", name="uq_indicative_entry_successor"),
        Index(
            "uq_indicative_entry_root",
            "workspace_id",
            "position_id",
            "rule_version",
            unique=True,
            postgresql_where=text("previous_assessment_id IS NULL"),
            sqlite_where=text("previous_assessment_id IS NULL"),
        ),
        Index("ix_indicative_entry_history", "workspace_id", "position_id", "recorded_at"),
        Index(
            "uq_indicative_family_root",
            "workspace_id",
            "position_id",
            unique=True,
            postgresql_where=text(f"previous_assessment_id IS NULL AND {FAMILY_FILTER}"),
            sqlite_where=text(f"previous_assessment_id IS NULL AND {FAMILY_FILTER}"),
        ),
        CheckConstraint(
            "outcome IN ('BELOW_ENTRY','AT_OR_ABOVE_ENTRY','NOT_REACHED','UNAVAILABLE','CLOSED')",
            name="indicative_entry_outcome",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    trade_id: Mapped[UUID] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id", ondelete="RESTRICT"))
    rule_version: Mapped[str] = mapped_column(String(64))
    previous_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT")
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    owner_basis_id: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(32))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ordering_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON())
    result: Mapped[dict[str, Any]] = mapped_column(JSON())


class IndicativeEntryEpisodeModel(Base):
    __tablename__ = "indicative_entry_episodes"
    __table_args__ = (
        UniqueConstraint(
            "opening_assessment_id", "kind", name="uq_indicative_entry_episode_opening"
        ),
        UniqueConstraint("alert_id", name="uq_indicative_entry_episode_alert"),
        UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "event_key",
            name="uq_indicative_review_event",
        ),
        UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "episode_number",
            name="uq_indicative_entry_episode_number",
        ),
        Index(
            "uq_indicative_entry_active",
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
            sqlite_where=text("closed_at IS NULL"),
        ),
        Index(
            "uq_indicative_family_active",
            "workspace_id",
            "position_id",
            "kind",
            unique=True,
            postgresql_where=text(f"closed_at IS NULL AND {FAMILY_FILTER}"),
            sqlite_where=text(f"closed_at IS NULL AND {FAMILY_FILTER}"),
        ),
        Index(
            "uq_indicative_family_event",
            "workspace_id",
            "position_id",
            "kind",
            "event_key",
            unique=True,
            postgresql_where=text(FAMILY_FILTER),
            sqlite_where=text(FAMILY_FILTER),
        ),
        Index(
            "uq_indicative_family_number",
            "workspace_id",
            "position_id",
            "kind",
            "episode_number",
            unique=True,
            postgresql_where=text(FAMILY_FILTER),
            sqlite_where=text(FAMILY_FILTER),
        ),
        CheckConstraint("episode_number > 0", name="indicative_entry_episode_positive"),
        CheckConstraint(
            "kind IN ('ENTRY_LOSS','REVIEW_DUE','DATA_UNAVAILABLE')",
            name="indicative_entry_kind",
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
        ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT")
    )
    closing_assessment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT")
    )
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alerts.id", ondelete="RESTRICT"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(100))
