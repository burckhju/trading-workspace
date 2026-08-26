"""SQLAlchemy persistence mappings for provider mappings and EOD prices."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    PriceType,
    QualityStatus,
)


def _enum(enum_type: type[Any], *, length: int) -> Enum:
    return Enum(
        enum_type,
        native_enum=False,
        length=length,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


class ProviderInstrumentMappingModel(Base):
    """Persisted provider symbol assigned to one internal market-data identity."""

    __tablename__ = "provider_instrument_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "listing_id",
            name="uq_provider_instrument_mappings_provider_listing",
        ),
        UniqueConstraint(
            "provider",
            "market_data_instrument_id",
            name="uq_provider_instrument_mappings_provider_instrument",
        ),
        UniqueConstraint(
            "provider",
            "provider_exchange_code",
            "provider_symbol",
            name="uq_provider_instrument_mappings_provider_symbol",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(provider_symbol)) > 0", name="provider_symbol_not_blank"),
        CheckConstraint(
            "length(trim(provider_exchange_code)) > 0",
            name="provider_exchange_code_not_blank",
        ),
        CheckConstraint(
            "listing_id IS NOT NULL OR market_data_instrument_id IS NOT NULL",
            name="internal_owner",
        ),
        Index("ix_provider_instrument_mappings_workspace_status", "workspace_id", "status"),
        Index(
            "ix_provider_instrument_mappings_workspace_instrument",
            "workspace_id",
            "market_data_instrument_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=True
    )
    market_data_instrument_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_data_instruments.id", ondelete="RESTRICT"), nullable=True
    )
    provider: Mapped[MarketDataProvider] = mapped_column(
        _enum(MarketDataProvider, length=30), nullable=False
    )
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_exchange_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[MappingStatus] = mapped_column(_enum(MappingStatus, length=20), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validation_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": False,
    }


class WarrantProviderMappingModel(Base):
    """Provider symbol assigned to one FT-004 WarrantListing."""

    __tablename__ = "warrant_provider_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider", "warrant_listing_id", name="uq_warrant_provider_mappings_provider_listing"
        ),
        UniqueConstraint(
            "provider",
            "provider_exchange_code",
            "provider_symbol",
            name="uq_warrant_provider_mappings_provider_symbol",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(trim(provider_symbol)) > 0", name="provider_symbol_not_blank"),
        CheckConstraint(
            "length(trim(provider_exchange_code)) > 0", name="provider_exchange_code_not_blank"
        ),
        Index("ix_warrant_provider_mappings_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_listings.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[MarketDataProvider] = mapped_column(
        _enum(MarketDataProvider, length=30), nullable=False
    )
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_exchange_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[MappingStatus] = mapped_column(_enum(MappingStatus, length=20), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validation_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": False,
    }


class DailyPriceModel(Base):
    """Persisted provider-independent completed end-of-day price."""

    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "trading_date",
            "price_type",
            name="uq_daily_prices_listing_date_type",
        ),
        UniqueConstraint(
            "market_data_instrument_id",
            "trading_date",
            "price_type",
            name="uq_daily_prices_instrument_date_type",
        ),
        CheckConstraint(
            "listing_id IS NOT NULL OR market_data_instrument_id IS NOT NULL",
            name="internal_owner",
        ),
        CheckConstraint("open > 0", name="open_positive"),
        CheckConstraint("high > 0", name="high_positive"),
        CheckConstraint("low > 0", name="low_positive"),
        CheckConstraint("close > 0", name="close_positive"),
        CheckConstraint(
            "adjusted_close IS NULL OR adjusted_close > 0",
            name="adjusted_close_positive",
        ),
        CheckConstraint("volume IS NULL OR volume >= 0", name="volume_non_negative"),
        CheckConstraint("low <= high", name="low_not_above_high"),
        CheckConstraint("open BETWEEN low AND high", name="open_in_range"),
        CheckConstraint("close BETWEEN low AND high", name="close_in_range"),
        Index("ix_daily_prices_listing_date", "listing_id", "trading_date"),
        Index(
            "ix_daily_prices_instrument_date",
            "market_data_instrument_id",
            "trading_date",
        ),
        Index("ix_daily_prices_workspace_date", "workspace_id", "trading_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=True
    )
    market_data_instrument_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_data_instruments.id", ondelete="RESTRICT"), nullable=True
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 6))
    currency: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[MarketDataProvider] = mapped_column(
        _enum(MarketDataProvider, length=30), nullable=False
    )
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_status: Mapped[QualityStatus] = mapped_column(
        _enum(QualityStatus, length=20), nullable=False
    )
    warnings: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    price_type: Mapped[PriceType] = mapped_column(_enum(PriceType, length=20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
