"""Provider-neutral identity for analyzable market-data instruments."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketDataInstrumentModel(Base):
    """Asset-type-neutral identity owned by exactly one internal semantic object."""

    __tablename__ = "market_data_instruments"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'LISTING' AND listing_id IS NOT NULL AND market_reference_id IS NULL) OR "
            "(kind = 'MARKET_REFERENCE' AND listing_id IS NULL AND market_reference_id IS NOT NULL)",
            name="ck_market_data_instruments_owner_matches_kind",
        ),
        UniqueConstraint(
            "workspace_id",
            "listing_id",
            name="uq_market_data_instruments_workspace_listing",
        ),
        UniqueConstraint(
            "workspace_id",
            "market_reference_id",
            name="uq_market_data_instruments_workspace_reference",
        ),
        Index(
            "ix_market_data_instruments_workspace_kind_active",
            "workspace_id",
            "kind",
            "active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    listing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="RESTRICT"), nullable=True
    )
    market_reference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_references.id", ondelete="RESTRICT"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
