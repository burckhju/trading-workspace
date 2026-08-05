"""Mapping between FT-001 domain entities and SQLAlchemy persistence models."""

from __future__ import annotations

from app.features.market.domain.entities import Listing, Underlying
from app.features.market.persistence.models import ListingModel, UnderlyingModel


def underlying_to_domain(model: UnderlyingModel) -> Underlying:
    return Underlying(
        id=model.id,
        workspace_id=model.workspace_id,
        type=model.type,
        name=model.name,
        isin=model.isin,
        wkn=model.wkn,
        lifecycle_status=model.lifecycle_status,
        quality_status=model.quality_status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        data_origin=model.data_origin,
    )


def listing_to_domain(model: ListingModel) -> Listing:
    return Listing(
        id=model.id,
        workspace_id=model.workspace_id,
        underlying_id=model.underlying_id,
        trading_venue_id=model.trading_venue_id,
        ticker=model.ticker,
        currency_code=model.currency_code,
        lifecycle_status=model.lifecycle_status,
        is_primary=model.is_primary,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        data_origin=model.data_origin,
    )


def apply_underlying(model: UnderlyingModel, domain: Underlying) -> None:
    model.name = domain.name
    model.isin = domain.isin
    model.wkn = domain.wkn
    model.lifecycle_status = domain.lifecycle_status
    model.quality_status = domain.quality_status
    model.version = domain.version
    model.updated_at = domain.updated_at


def apply_listing(model: ListingModel, domain: Listing) -> None:
    model.trading_venue_id = domain.trading_venue_id
    model.ticker = domain.ticker
    model.currency_code = domain.currency_code
    model.lifecycle_status = domain.lifecycle_status
    model.is_primary = domain.is_primary
    model.version = domain.version
    model.updated_at = domain.updated_at
