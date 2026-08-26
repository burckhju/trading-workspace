"""Conversions between immutable domain values and persistence records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.features.market_data.domain.errors import InvalidDailyPrice
from app.features.market_data.domain.models import DailyPrice, ProviderInstrumentMapping
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)

_WARNING_SEPARATOR = "\n"


def mapping_to_domain(
    model: ProviderInstrumentMappingModel,
) -> ProviderInstrumentMapping:
    """Convert a persisted provider mapping to its domain representation."""
    return ProviderInstrumentMapping(
        id=model.id,
        workspace_id=model.workspace_id,
        listing_id=model.listing_id,
        provider=model.provider,
        provider_symbol=model.provider_symbol,
        provider_exchange_code=model.provider_exchange_code,
        status=model.status,
        validated_at=model.validated_at,
        validation_message=model.validation_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
        version=model.version,
        market_data_instrument_id=model.market_data_instrument_id,
    )


def mapping_to_model(
    value: ProviderInstrumentMapping,
) -> ProviderInstrumentMappingModel:
    """Convert a domain provider mapping to a new persistence record."""
    return ProviderInstrumentMappingModel(
        id=value.id,
        workspace_id=value.workspace_id,
        listing_id=value.listing_id,
        market_data_instrument_id=value.market_data_instrument_id,
        provider=value.provider,
        provider_symbol=value.provider_symbol,
        provider_exchange_code=value.provider_exchange_code,
        status=value.status,
        validated_at=value.validated_at,
        validation_message=value.validation_message,
        created_at=value.created_at,
        updated_at=value.updated_at,
        version=value.version,
    )


def daily_price_to_domain(model: DailyPriceModel) -> DailyPrice:
    """Convert one listing-owned persisted EOD price to its domain representation."""
    if model.listing_id is None:
        raise InvalidDailyPrice(
            "instrument-only daily price is outside the D01-C listing-scoped domain contract",
            field="listing_id",
        )
    return DailyPrice(
        listing_id=model.listing_id,
        market_data_instrument_id=getattr(model, "market_data_instrument_id", None),
        trading_date=model.trading_date,
        open=model.open,
        high=model.high,
        low=model.low,
        close=model.close,
        adjusted_close=model.adjusted_close,
        volume=model.volume,
        currency=model.currency,
        provider=model.provider,
        provider_symbol=model.provider_symbol,
        retrieved_at=model.retrieved_at,
        source_updated_at=model.source_updated_at,
        quality_status=model.quality_status,
        warnings=tuple(filter(None, model.warnings.split(_WARNING_SEPARATOR))),
        price_type=model.price_type,
    )


def daily_price_to_model(
    value: DailyPrice,
    *,
    workspace_id: UUID,
    price_id: UUID,
    now: datetime,
    market_data_instrument_id: UUID | None = None,
) -> DailyPriceModel:
    """Convert an EOD domain value to a new persistence record."""
    return DailyPriceModel(
        id=price_id,
        workspace_id=workspace_id,
        listing_id=value.listing_id,
        market_data_instrument_id=(
            market_data_instrument_id
            if market_data_instrument_id is not None
            else value.market_data_instrument_id
        ),
        trading_date=value.trading_date,
        open=value.open,
        high=value.high,
        low=value.low,
        close=value.close,
        adjusted_close=value.adjusted_close,
        volume=value.volume,
        currency=value.currency,
        provider=value.provider,
        provider_symbol=value.provider_symbol,
        retrieved_at=value.retrieved_at,
        source_updated_at=value.source_updated_at,
        quality_status=value.quality_status,
        warnings=_WARNING_SEPARATOR.join(value.warnings),
        price_type=value.price_type,
        created_at=now,
        updated_at=now,
    )


def apply_daily_price(model: DailyPriceModel, value: DailyPrice, *, now: datetime) -> bool:
    """Apply changed provider fields and report whether persistence state changed."""
    fields = (
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
        "currency",
        "provider",
        "provider_symbol",
        "retrieved_at",
        "source_updated_at",
        "quality_status",
        "price_type",
    )
    changed = False
    for field in fields:
        incoming = getattr(value, field)
        if getattr(model, field) != incoming:
            setattr(model, field, incoming)
            changed = True
    warnings = _WARNING_SEPARATOR.join(value.warnings)
    if model.warnings != warnings:
        model.warnings = warnings
        changed = True
    if changed:
        model.updated_at = now
    return changed
