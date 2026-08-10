"""Persistence models for provider-neutral top-down reference data."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketReferenceModel(Base):
    __tablename__ = "market_references"
    __table_args__ = (
        UniqueConstraint("workspace_id", "code", name="uq_market_references_workspace_code"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_version: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SectorModel(Base):
    __tablename__ = "sectors"
    __table_args__ = (UniqueConstraint("workspace_id", "code", name="uq_sectors_workspace_code"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    classification_system: Mapped[str] = mapped_column(String(100), nullable=False)
    classification_version: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UnderlyingSectorAssignmentModel(Base):
    __tablename__ = "underlying_sector_assignments"
    __table_args__ = (
        Index("ix_underlying_sector_assignments_underlying_valid", "underlying_id", "valid_from"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="CASCADE"), nullable=False
    )
    sector_id: Mapped[UUID] = mapped_column(
        ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200))
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SectorReferenceAssignmentModel(Base):
    __tablename__ = "sector_reference_assignments"
    __table_args__ = (
        Index("ix_sector_reference_assignments_sector_valid", "sector_id", "valid_from"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    sector_id: Mapped[UUID] = mapped_column(
        ForeignKey("sectors.id", ondelete="CASCADE"), nullable=False
    )
    market_reference_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_references.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UnderlyingBenchmarkAssignmentModel(Base):
    """Historized semantic benchmark assignment for an underlying."""

    __tablename__ = "underlying_benchmark_assignments"
    __table_args__ = (
        Index(
            "ix_underlying_benchmark_assignments_underlying_role_valid",
            "underlying_id",
            "role",
            "valid_from",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="CASCADE"), nullable=False
    )
    market_reference_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_references.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200))
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketReferenceListingAssignmentModel(Base):
    """Historized bridge from a semantic market reference to an analyzable listing."""

    __tablename__ = "market_reference_listing_assignments"
    __table_args__ = (
        Index(
            "ix_market_reference_listing_assignments_reference_valid",
            "market_reference_id",
            "valid_from",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    market_reference_id: Mapped[UUID] = mapped_column(
        ForeignKey("market_references.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200))
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
