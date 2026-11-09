"""An ETF proof cannot validate a stock, another listing or a stale identity."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_catalog_mapping_validation import (
    evidence,
)

import app.features.market_data.service.etf_mapping_validation as validation_module
from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.service.etf_mapping_validation import (
    EtfCatalogMappingResolver,
    _evidence_message,
)
from app.providers.eodhd.etf_catalog import EtfCatalogIdentity


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [None, "stock", "mic", "ticker", "expired", "identity", "workspace"]
)
async def test_revalidates_exact_etf_owner_and_live_proof(failure):
    mapping, old, listing, underlying, venue = evidence()
    item = replace(old.item, instrument_type="ETF")
    proof = EtfCatalogIdentity(
        item,
        "ARCX",
        "/exchange-symbol-list/US",
        old.catalog_retrieved_at,
        old.exchanges_retrieved_at,
        item.provider_symbol,
        "https://issuer.example/fund",
        datetime.now(UTC).date(),
        "https://exchange.example/venue",
        "NYSE ARCA",
    )
    listing.ticker, underlying.type, venue.mic = item.provider_symbol, "ETF", "ARCX"
    if failure == "stock":
        underlying.type = "STOCK"
    if failure == "mic":
        venue.mic = "XNYS"
    if failure == "ticker":
        listing.ticker = "OTHER"
    if failure == "expired":
        proof = replace(proof, catalog_retrieved_at=datetime.now(UTC) - timedelta(days=1))
    if failure == "identity":
        underlying.isin = "US0000000002"
    if failure == "workspace":
        listing.workspace_id = None
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await EtfCatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert result.status == (MappingStatus.INVALID if failure else MappingStatus.ACTIVE)
    if failure is None:
        message = json.loads(result.message)
        assert message["source"] == "EODHD_ETF_AND_REVIEWED_LISTING_V1"
        assert message["mic"] == "ARCX" and len(message["listing_sha256"]) == 64
        assert len(_evidence_message(replace(proof, search_retrieved_at=datetime.now(UTC)))) <= 500


def etf_evidence(mic="ARCX"):
    mapping, old, listing, underlying, venue = evidence()
    ticker, isin = ("XLE", "US81369Y5069") if mic == "ARCX" else ("QQQ", "US46090E1038")
    mapping = replace(mapping, provider_symbol=ticker)
    item = replace(old.item, provider_symbol=ticker, instrument_type="ETF", isin=isin)
    proof = EtfCatalogIdentity(
        item,
        mic,
        "/exchange-symbol-list/US",
        old.catalog_retrieved_at,
        old.exchanges_retrieved_at,
        ticker,
        "https://issuer.example/fund",
        datetime.now(UTC).date(),
        "https://exchange.example/venue",
        "NYSE ARCA" if mic == "ARCX" else "NASDAQ",
    )
    listing.ticker = ticker
    underlying.type, underlying.isin, venue.mic = "ETF", isin, mic
    return mapping, proof, listing, underlying, venue


@pytest.mark.asyncio
@pytest.mark.parametrize("mic", ["ARCX", "XNMS"])
async def test_reviewed_segment_is_required_even_when_the_operating_venue_matches(mic):
    mapping, proof, listing, underlying, venue = etf_evidence(mic)
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    good = await EtfCatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert good.status is MappingStatus.ACTIVE
    assert json.loads(good.message)["mic"] == mic
    venue.mic = "XNYS" if mic == "ARCX" else "XNAS"
    session.get = AsyncMock(side_effect=[listing, underlying, venue])
    bad = await EtfCatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert bad.status is MappingStatus.INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        "mapping_workspace",
        "mapping_listing",
        "mapping_symbol",
        "mapping_exchange",
        "listing_currency",
        "inactive_listing",
        "underlying_workspace",
        "inactive_underlying",
        "inactive_venue",
        "no_listing",
        "no_underlying",
        "no_venue",
        "proof_type",
        "proof_endpoint",
        "provider_venue",
        "unreviewed_segment",
    ],
)
async def test_changed_owner_or_provider_binding_is_rejected_without_mutations(failure):
    mapping, proof, listing, underlying, venue = etf_evidence()
    workspace_id, listing_id = mapping.workspace_id, mapping.listing_id
    if failure == "mapping_workspace":
        mapping = replace(mapping, workspace_id=uuid4())
    elif failure == "mapping_listing":
        mapping = replace(mapping, listing_id=uuid4())
    elif failure == "mapping_symbol":
        mapping = replace(mapping, provider_symbol="OTHER")
    elif failure == "mapping_exchange":
        mapping = replace(mapping, provider_exchange_code="PA")
    elif failure == "listing_currency":
        listing.currency_code = "EUR"
    elif failure == "inactive_listing":
        listing.lifecycle_status = "INACTIVE"
    elif failure == "underlying_workspace":
        underlying.workspace_id = uuid4()
    elif failure == "inactive_underlying":
        underlying.lifecycle_status = "INACTIVE"
    elif failure == "inactive_venue":
        venue.is_active = False
    elif failure == "no_listing":
        listing = None
    elif failure == "no_underlying":
        underlying = None
    elif failure == "no_venue":
        venue = None
    elif failure == "proof_type":
        proof = replace(proof, item=replace(proof.item, instrument_type="FUND"))
    elif failure == "proof_endpoint":
        proof = replace(proof, endpoint="/search/XLE")
    elif failure == "provider_venue":
        proof = replace(proof, provider_venue="NYSE")
    elif failure == "unreviewed_segment":
        proof, venue.mic = replace(proof, mic="XNYS"), "XNYS"
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await EtfCatalogMappingResolver(
        session, workspace_id, listing_id, proof
    ).validate_mapping(mapping)
    assert result.status is MappingStatus.INVALID
    assert result.message == "ETF_EVIDENCE_EXPIRED_OR_LISTING_IDENTITY_CHANGED"
    assert all(call.kwargs == {"populate_existing": True} for call in session.get.call_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stamp_field",
    ["catalog_retrieved_at", "exchanges_retrieved_at", "search_retrieved_at"],
)
@pytest.mark.parametrize(
    "age,expected",
    [
        (timedelta(microseconds=-1), MappingStatus.INVALID),
        (timedelta(hours=24), MappingStatus.INVALID),
        (timedelta(hours=24, microseconds=-1), MappingStatus.ACTIVE),
    ],
)
async def test_every_live_proof_has_an_independent_half_open_24_hour_window(
    monkeypatch, stamp_field, age, expected
):
    mapping, proof, listing, underlying, venue = etf_evidence()
    now = datetime.now(UTC)
    monkeypatch.setattr(validation_module, "datetime", SimpleNamespace(now=lambda _: now))
    proof = replace(
        proof,
        catalog_retrieved_at=now,
        exchanges_retrieved_at=now,
        search_endpoint=f"/search/{proof.item.isin}",
        search_retrieved_at=now,
    )
    proof = replace(proof, **{stamp_field: now - age})
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await EtfCatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert result.status is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["no_time", "no_endpoint", "other_isin"])
async def test_search_evidence_must_bind_its_timestamp_and_exact_isin(failure):
    mapping, proof, listing, underlying, venue = etf_evidence()
    proof = replace(
        proof,
        search_endpoint=f"/search/{proof.item.isin}",
        search_retrieved_at=datetime.now(UTC),
    )
    if failure == "no_time":
        proof = replace(proof, search_retrieved_at=None)
    elif failure == "no_endpoint":
        proof = replace(proof, search_endpoint=None)
    else:
        proof = replace(proof, search_endpoint="/search/US0000000002")
    session = SimpleNamespace(get=AsyncMock(side_effect=[listing, underlying, venue]))
    result = await EtfCatalogMappingResolver(
        session, mapping.workspace_id, mapping.listing_id, proof
    ).validate_mapping(mapping)
    assert result.status is MappingStatus.INVALID


@pytest.mark.parametrize("mic", ["ARCX", "XNMS"])
@pytest.mark.parametrize("symbol_length", [32, 64])
def test_full_provenance_fits_owner_field_without_dropping_search_or_segment(mic, symbol_length):
    mapping, proof, _, _, _ = etf_evidence(mic)
    now = datetime(2026, 11, 9, 12, 34, 56, 123456, tzinfo=UTC)
    proof = replace(
        proof,
        item=replace(proof.item, provider_symbol="S" * symbol_length),
        listing_ticker="S" * symbol_length,
        listing_source_url="https://issuer.example/" + "x" * 900,
        venue_source_url="https://exchange.example/" + "y" * 900,
        catalog_retrieved_at=now,
        exchanges_retrieved_at=now,
        search_endpoint=f"/search/{proof.item.isin}",
        search_retrieved_at=now,
    )
    message = _evidence_message(proof)
    parsed = json.loads(message)
    assert len(message) <= 500
    assert parsed["symbol"] == "S" * symbol_length
    assert parsed["mic"] == mic and parsed["isin"] == proof.item.isin
    assert parsed["search_at"] == parsed["catalog_at"] == parsed["exchanges_at"] == now.isoformat()
    assert len(parsed["listing_sha256"]) == 64
    assert replace(mapping, validation_message=message).validation_message == message
    changed = json.loads(
        _evidence_message(replace(proof, listing_source_url="https://new.example/"))
    )
    assert changed["listing_sha256"] != parsed["listing_sha256"]
