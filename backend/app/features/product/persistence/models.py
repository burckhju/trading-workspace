"""FT-004 warrant persistence mappings."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.product.domain.models import OptionDirection, ProductFamily, WarrantLifecycle


def _enum(enum_type: type[Any], *, length: int) -> Enum:
    return Enum(
        enum_type,
        native_enum=False,
        length=length,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


class WarrantModel(Base):
    __tablename__ = "warrants"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_blank"),
        Index(
            "uq_warrants_workspace_isin",
            "workspace_id",
            "isin",
            unique=True,
            postgresql_where=text("isin IS NOT NULL"),
        ),
        Index(
            "uq_warrants_workspace_wkn",
            "workspace_id",
            "wkn",
            unique=True,
            postgresql_where=text("wkn IS NOT NULL"),
        ),
        Index("ix_warrants_workspace_underlying", "workspace_id", "underlying_id"),
        Index("ix_warrants_workspace_issuer", "workspace_id", "issuer_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    issuer_id: Mapped[UUID] = mapped_column(
        ForeignKey("issuers.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False
    )
    product_family: Mapped[ProductFamily] = mapped_column(
        _enum(ProductFamily, length=20), nullable=False, default=ProductFamily.WARRANT
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    wkn: Mapped[str | None] = mapped_column(String(16), nullable=True)
    lifecycle_status: Mapped[WarrantLifecycle] = mapped_column(
        _enum(WarrantLifecycle, length=20), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __mapper_args__ = MappingProxyType(
        {
            "version_id_col": version,
            "version_id_generator": False,
        }
    )


class WarrantTermsVersionModel(Base):
    __tablename__ = "warrant_terms_versions"
    __table_args__ = (
        UniqueConstraint(
            "warrant_id", "version_no", name="uq_warrant_terms_versions_warrant_version"
        ),
        CheckConstraint("version_no >= 1", name="version_no_positive"),
        CheckConstraint("strike >= 0", name="strike_non_negative"),
        CheckConstraint("ratio > 0", name="ratio_positive"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="effective_window_valid"
        ),
        Index(
            "uq_warrant_terms_versions_open",
            "warrant_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    warrant_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrants.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    option_direction: Mapped[OptionDirection] = mapped_column(
        _enum(OptionDirection, length=10), nullable=False
    )
    strike: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    maturity_date: Mapped[date] = mapped_column(Date, nullable=False)
    ratio: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WarrantListingModel(Base):
    __tablename__ = "warrant_listings"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "trading_venue_id",
            "symbol",
            name="uq_warrant_listings_workspace_venue_symbol",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(symbol)) > 0", name="symbol_not_blank"),
        Index("ix_warrant_listings_warrant_lifecycle", "warrant_id", "lifecycle_status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrants.id", ondelete="RESTRICT"), nullable=False
    )
    trading_venue_id: Mapped[UUID] = mapped_column(
        ForeignKey("trading_venues.id", ondelete="RESTRICT"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    quotation_currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    lifecycle_status: Mapped[WarrantLifecycle] = mapped_column(
        _enum(WarrantLifecycle, length=20), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __mapper_args__ = MappingProxyType(
        {
            "version_id_col": version,
            "version_id_generator": False,
        }
    )
