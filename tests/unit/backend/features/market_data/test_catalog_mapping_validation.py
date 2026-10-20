"""Catalog proof cannot activate another identity or cross workspace boundaries."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_mapping_administration import Uow
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.service.catalog_mapping_validation import CatalogMappingResolver
from app.features.market_data.service.types import ProviderInstrumentSearchItem
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VenueReconciliationStatus,
    VerifiedListingVenue,
)
from app.providers.eodhd.stock_catalog import StockCatalogIdentity


def evidence():
    _, _, mapping = make_adapter()
    now = datetime.now(UTC)
    proof = StockCatalogIdentity(
        ProviderInstrumentSearchItem(
            MarketDataProvider.EODHD,
            mapping.provider_symbol,
            "US",
            currency="USD",
            isin="US0000000001",
        ),
        "XNAS",
        "/exchange-symbol-list/NASDAQ",
        now,
        now,
    )
    listing = SimpleNamespace(
        workspace_id=mapping.workspace_id,
        underlying_id=uuid4(),
        trading_venue_id=uuid4(),
        currency_code="USD",
        lifecycle_status="ACTIVE",
    )
    underlying = SimpleNamespace(
        workspace_id=mapping.workspace_id, isin=proof.item.isin, lifecycle_status="ACTIVE"
    )
    venue = SimpleNamespace(mic="XNAS", is_active=True)
    return mapping, proof, listing, underlying, venue


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        None,
        "expired",
        "future",
        "workspace",
        "listing",
        "symbol",
        "exchange",
        "listing_currency",
        "underlying_isin",
        "underlying_workspace",
        "inactive_stock",
        "inactive_listing",
        "inactive_venue",
        "mic",
        "no_listing",
        "no_underlying",
        "no_venue",
    ],
)
async def test_catalog_validation_rechecks_owner_identity_lifecycle_and_evidence_age(failure):
    mapping, proof, listing, underlying, venue = evidence()
    expected_workspace, expected_listing = mapping.workspace_id, mapping.listing_id
    if failure == "expired":
        proof = replace(proof, catalog_retrieved_at=datetime.now(UTC) - timedelta(days=1))
    if failure == "future":
        proof = replace(proof, exchanges_retrieved_at=datetime.now(UTC) + timedelta(minutes=5))
    if failure == "workspace":
        mapping = replace(mapping, workspace_id=uuid4())
    if failure == "listing":
        mapping = replace(mapping, listing_id=uuid4())
    if failure == "symbol":
        mapping = replace(mapping, provider_symbol="OTHER")
    if failure == "exchange":
        mapping = replace(mapping, provider_exchange_code="PA")
    if failure == "listing_currency":
        listing.currency_code = "EUR"
    if failure == "underlying_isin":
        underlying.isin = "US0000000002"
    if failure == "underlying_workspace":
        underlying.workspace_id = uuid4()
    if failure == "inactive_stock":
        underlying.lifecycle_status = "INACTIVE"
    if failure == "inactive_listing":
        listing.lifecycle_status = "INACTIVE"
    if failure == "inactive_venue":
        venue.is_active = False
    if failure == "mic":
        venue.mic = "XNYS"
    if failure == "no_listing":
        listing = None
    if failure == "no_underlying":
        underlying = None
    if failure == "no_venue":
        venue = None
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await CatalogMappingResolver(
        session, expected_workspace, expected_listing, proof
    ).validate_mapping(mapping)
    assert result.status == (MappingStatus.ACTIVE if failure is None else MappingStatus.INVALID)
    if failure is None:
        details = json.loads(result.message)
        assert details["isin"] == proof.item.isin and details["mic"] == "XNAS"
        assert details["catalog_retrieved_at"] == proof.catalog_retrieved_at.isoformat()
        assert details["provider_exchange_code"] == "US"
    else:
        assert result.message == "CATALOG_EVIDENCE_EXPIRED_OR_IDENTITY_CHANGED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [None, "workspace", "listing", "provider", "exchange", "venue", "missing_venue"]
)
async def test_instrument_proof_overrides_global_us_history_only_for_exact_scope(failure):
    uow = Uow()
    workspace, listing, venue_id = uuid4(), uuid4(), uuid4()
    proof = VerifiedListingVenue(workspace, listing, MarketDataProvider.EODHD, "US", venue_id)
    uow.mappings.listing_venues[listing] = venue_id
    uow.mappings.exchange_venues["US"] = [venue_id, uuid4()]
    if failure == "workspace":
        proof = replace(proof, workspace_id=uuid4())
    if failure == "listing":
        proof = replace(proof, listing_id=uuid4())
    if failure == "provider":
        proof = replace(proof, provider="OTHER")
    if failure == "exchange":
        proof = replace(proof, provider_exchange_code="PA")
    if failure == "venue":
        proof = replace(proof, venue_id=uuid4())
    if failure == "missing_venue":
        uow.mappings.listing_venues.clear()
    result = await ProviderVenueReconciliationService(uow, verified_listing=proof).reconcile(
        workspace, listing, MarketDataProvider.EODHD, "US"
    )
    expected = VenueReconciliationStatus.AMBIGUOUS
    if failure is None:
        expected = VenueReconciliationStatus.MATCHED
    if failure == "venue":
        expected = VenueReconciliationStatus.CONFLICT
    if failure == "missing_venue":
        expected = VenueReconciliationStatus.UNRESOLVED
    assert result.status == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [None, "expired", "future", "missing_time", "wrong_isin", "missing_endpoint"]
)
async def test_search_proof_is_scoped_fresh_complete_and_preserved(failure):
    mapping, proof, listing, underlying, venue = evidence()
    now = datetime.now(UTC)
    proof = replace(proof, search_endpoint=f"/search/{proof.item.isin}", search_retrieved_at=now)
    if failure == "expired":
        proof = replace(proof, search_retrieved_at=now - timedelta(days=1))
    if failure == "future":
        proof = replace(proof, search_retrieved_at=now + timedelta(minutes=1))
    if failure == "missing_time":
        proof = replace(proof, search_retrieved_at=None)
    if failure == "wrong_isin":
        proof = replace(proof, search_endpoint="/search/OTHER")
    if failure == "missing_endpoint":
        proof = replace(proof, search_endpoint=None)
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await CatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert result.status == (MappingStatus.ACTIVE if failure is None else MappingStatus.INVALID)
    if failure is None:
        data = json.loads(result.message)
        assert data["source"] == "EODHD_ISIN_CATALOG_V1"
        assert data["search_at"] == proof.search_retrieved_at.isoformat()
        assert data["catalog_at"] == proof.catalog_retrieved_at.isoformat()
        assert data["exchanges_at"] == proof.exchanges_retrieved_at.isoformat()
        assert data["isin"] == proof.item.isin
        assert data["search"] == f"/search/{proof.item.isin}"


def test_search_provenance_fits_existing_field_at_maximum_supported_identity_lengths():
    from app.features.market_data.service.catalog_mapping_validation import _evidence_message

    _, proof, _, _, _ = evidence()
    proof = replace(
        proof,
        item=replace(proof.item, provider_symbol="S" * 64, provider_exchange_code="E" * 32),
        endpoint="/exchange-symbol-list/" + "E" * 32,
        search_endpoint=f"/search/{proof.item.isin}",
        search_retrieved_at=datetime.now(UTC),
    )
    assert len(_evidence_message(proof)) <= 500
