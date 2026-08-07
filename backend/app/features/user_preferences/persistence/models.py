"""Persistence models for user-scoped UI preferences."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserPreferenceModel(Base):
    """Named preference document scoped to workspace, actor and preference kind."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "actor_id",
            "kind",
            "name",
            name="uq_user_preferences_scope_name",
        ),
        Index("ix_user_preferences_scope", "workspace_id", "actor_id", "kind"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
