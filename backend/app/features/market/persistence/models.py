"""SQLAlchemy mappings for the FT-001 physical data model.

These classes represent persistence state only. Business behavior remains in the
SQLAlchemy-independent domain layer implemented in a later sprint step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.features.market.persistence.enums import (
    ActorType,
    AggregateType,
    ChangeType,
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)


def _enum(enum_type: type[Any], *, length: int) -> Enum:
    return Enum(
        enum_type,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    underlyings: Mapped[list[UnderlyingModel]] = relationship(
        back_populates="workspace"
    )
    listings: Mapped[list[ListingModel]] = relationship(back_populates="workspace")
    audit_events: Mapped[list[AuditEventModel]] = relationship(
        back_populates="workspace"
    )


class TradingVenueModel(Base):
    __tablename__ = "trading_venues"
    __table_args__ = (
        UniqueConstraint("mic", name="uq_trading_venues_mic"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    mic: Mapped[str] = mapped_column(String(4), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reference_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    listings: Mapped[list[ListingModel]] = relationship(back_populates="trading_venue")


class CurrencyModel(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint("minor_unit BETWEEN 0 AND 6", name="minor_unit_range"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    minor_unit: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reference_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    listings: Mapped[list[ListingModel]] = relationship(back_populates="currency")


class UnderlyingModel(Base):
    __tablename__ = "underlyings"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index(
            "uq_underlyings_workspace_isin",
            "workspace_id",
            "isin",
            unique=True,
            postgresql_where=text("isin IS NOT NULL"),
        ),
        Index(
            "uq_underlyings_workspace_wkn",
            "workspace_id",
            "wkn",
            unique=True,
            postgresql_where=text("wkn IS NOT NULL"),
        ),
        Index(
            "ix_underlyings_workspace_lifecycle_name",
            "workspace_id",
            "lifecycle_status",
            "name",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[UnderlyingType] = mapped_column(
        _enum(UnderlyingType, length=20), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    wkn: Mapped[str | None] = mapped_column(String(6))
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        _enum(LifecycleStatus, length=20), nullable=False
    )
    quality_status: Mapped[QualityStatus] = mapped_column(
        _enum(QualityStatus, length=20), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, length=20), nullable=False
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="underlyings")
    listings: Mapped[list[ListingModel]] = relationship(
        back_populates="underlying",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": False,
    }


class ListingModel(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "trading_venue_id",
            "ticker",
            name="uq_listings_workspace_venue_ticker",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(ticker)) > 0", name="ticker_not_blank"),
        Index(
            "uq_listings_active_primary_underlying",
            "underlying_id",
            unique=True,
            postgresql_where=text("is_primary = true AND lifecycle_status = 'ACTIVE'"),
        ),
        Index("ix_listings_underlying_lifecycle", "underlying_id", "lifecycle_status"),
        Index("ix_listings_workspace_ticker", "workspace_id", "ticker"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="CASCADE"), nullable=False
    )
    trading_venue_id: Mapped[UUID] = mapped_column(
        ForeignKey("trading_venues.id", ondelete="RESTRICT"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        _enum(LifecycleStatus, length=20), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, length=20), nullable=False
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="listings")
    underlying: Mapped[UnderlyingModel] = relationship(back_populates="listings")
    trading_venue: Mapped[TradingVenueModel] = relationship(back_populates="listings")
    currency: Mapped[CurrencyModel] = relationship(back_populates="listings")

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": False,
    }


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "ix_audit_events_aggregate_chronology",
            "workspace_id",
            "aggregate_type",
            "aggregate_id",
            text("occurred_at DESC"),
        ),
        Index(
            "ix_audit_events_workspace_chronology",
            "workspace_id",
            text("occurred_at DESC"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    aggregate_type: Mapped[AggregateType] = mapped_column(
        _enum(AggregateType, length=30), nullable=False
    )
    aggregate_id: Mapped[UUID] = mapped_column(nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actor_type: Mapped[ActorType] = mapped_column(
        _enum(ActorType, length=20), nullable=False
    )
    actor_id: Mapped[str | None] = mapped_column(String(100))
    actor_display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, length=20), nullable=False
    )
    change_type: Mapped[ChangeType] = mapped_column(
        _enum(ChangeType, length=30), nullable=False
    )
    version_before: Mapped[int | None] = mapped_column(Integer)
    version_after: Mapped[int | None] = mapped_column(Integer)
    field_changes: Mapped[dict[str, dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="audit_events")
