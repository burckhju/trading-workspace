"""Persistence model for explicit FT-013 runtime activation history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ModelRuntimeActivationRecord(Base):
    __tablename__ = "model_runtime_activations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_runtime_activation_workspace",
        ),
        ForeignKeyConstraint(
            ["model_id"],
            ["governed_models.id"],
            ondelete="RESTRICT",
            name="fk_runtime_activation_model",
        ),
        ForeignKeyConstraint(
            ["model_version_id"],
            ["governed_model_versions.id"],
            ondelete="RESTRICT",
            name="fk_runtime_activation_version",
        ),
        Index("ix_runtime_activation_model_activated", "model_id", "activated_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    model_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    model_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
