"""Durable, explicitly activated chart membership and setup attempt facts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ChartWatchlistModel(Base):
    __tablename__ = "chart_watchlists"
    __table_args__ = (
        CheckConstraint("length(catalog_checksum) = 64", name="catalog_checksum_shape"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True
    )
    catalog_version: Mapped[str] = mapped_column(String(80), nullable=False)
    catalog_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_by: Mapped[str | None] = mapped_column(String(200))
    activated_by_name: Mapped[str] = mapped_column(String(200), nullable=False)


class ChartWatchlistMemberModel(Base):
    __tablename__ = "chart_watchlist_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "ordinal", name="uq_chart_watchlist_member_order"),
        CheckConstraint("ordinal >= 0 AND ordinal < 100", name="member_order"),
        CheckConstraint("kind IN ('INDEX', 'ETF')", name="member_kind"),
        CheckConstraint(
            "(kind = 'INDEX' AND listing_id IS NULL) OR "
            "(kind = 'ETF' AND market_reference_id IS NULL)",
            name="member_owner_kind",
        ),
        CheckConstraint(
            "(created_mapping_id IS NULL AND created_mapping_version IS NULL) OR "
            "(created_mapping_id IS NOT NULL AND created_mapping_version >= 1)",
            name="created_mapping_evidence",
        ),
        CheckConstraint(
            "(verified_mapping_id IS NULL AND verified_mapping_version IS NULL "
            "AND verified_provider_symbol IS NULL AND verified_provider_exchange_code IS NULL "
            "AND setup_completed_at IS NULL) OR "
            "(verified_mapping_id IS NOT NULL AND verified_mapping_version >= 1 "
            "AND verified_provider_symbol IS NOT NULL "
            "AND verified_provider_exchange_code IS NOT NULL AND setup_completed_at IS NOT NULL)",
            name="verified_mapping_evidence",
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("chart_watchlists.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    market_reference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_references.id", ondelete="RESTRICT")
    )
    created_mapping_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "provider_instrument_mappings.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        )
    )
    created_mapping_version: Mapped[int | None] = mapped_column(Integer)
    verified_mapping_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("provider_instrument_mappings.id", ondelete="RESTRICT")
    )
    verified_mapping_version: Mapped[int | None] = mapped_column(Integer)
    verified_provider_symbol: Mapped[str | None] = mapped_column(String(64))
    verified_provider_exchange_code: Mapped[str | None] = mapped_column(String(32))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_reason: Mapped[str | None] = mapped_column(String(120))
    setup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
