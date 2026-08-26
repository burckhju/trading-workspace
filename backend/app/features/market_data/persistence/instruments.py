"""Provider-neutral persistence identity for market-data addressing."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketDataInstrumentModel(Base):
    """Stable market-data identity owned by exactly one internal owner."""

    __tablename__ = "market_data_instruments"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'LISTING' AND listing_id IS NOT NULL AND market_reference_id IS NULL) OR "
            "(kind = 'MARKET_REFERENCE' AND listing_id IS NULL "
            "AND market_reference_id IS NOT NULL)",
            name="owner_matches_kind",
        ),
        UniqueConstraint("listing_id", name="uq_market_data_instruments_listing"),
        UniqueConstraint(
            "market_reference_id",
            name="uq_market_data_instruments_market_reference",
        ),
        Index("ix_market_data_instruments_workspace_kind", "workspace_id", "kind"),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
