"""Original published schedules for indicative reference-market review only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ReviewCalendarModel(Base):
    __tablename__ = "review_calendar_sources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_version", name="uq_review_calendar_version"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    venue_mic: Mapped[str] = mapped_column(String(4))
    source_version: Mapped[str] = mapped_column(String(100))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64))
