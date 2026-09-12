"""Immutable reference releases, separate from locally enabled currency rows."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CurrencyCatalogReleaseModel(Base):
    __tablename__ = "currency_catalog_releases"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CurrencyCatalogStateModel(Base):
    __tablename__ = "currency_catalog_state"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("currency_catalog_releases.id", ondelete="RESTRICT"), nullable=True
    )
