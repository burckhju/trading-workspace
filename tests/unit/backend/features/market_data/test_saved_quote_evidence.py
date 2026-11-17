"""Held-product binding and honest provenance for the current saved quote."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_quote_evidence import (
    OriginalQuoteEvidence,
    OriginalQuoteSideEvidence,
)
from app.features.market_data.persistence.quote_identity import QuoteIdentity, verified_identity
from app.features.market_data.service import risk_read
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.types import MarketDataResult
from app.features.product.domain.models import WarrantLifecycle

NOW = datetime(2026, 11, 15, 10, tzinfo=UTC)
RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])


def original_evidence():
    bid_at = NOW - timedelta(seconds=60)
    ask_at = NOW - timedelta(seconds=120)
    return OriginalQuoteEvidence(
        version="original-quote-evidence-v1",
        source_contract="frankfurt-quotes-v1",
        source_reference="Synthetic Frankfurt snapshot, no provider contact",
        generated_at=NOW - timedelta(seconds=10),
        isin="DE000AB00001",
        currency="EUR",
        venue_mic="XFRA",
        bid=OriginalQuoteSideEvidence(Decimal("2.1"), bid_at, bid_at.isoformat(), "bid_at"),
        ask=OriginalQuoteSideEvidence(Decimal("2.2"), ask_at, ask_at.isoformat(), "ask_at"),
    )


def fixture(monkeypatch, *, original=True):
    workspace, position, warrant, listing, venue = (uuid4() for _ in range(5))
    identity = QuoteIdentity(
        "current-route",
        "DE000AB00001",
        "AB0000",
        "EUR",
        "XFRA",
        "XFRA",
        workspace_id=workspace,
        warrant_id=warrant,
        warrant_listing_id=listing,
        trading_venue_id=venue,
    )
    selection = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace,
        position_id=position,
        selection_status="SELECTED",
        warrant_listing_id=listing,
        provider="FRANKFURT_QUOTES",
        identity_key=identity.key,
        selected_at=NOW - timedelta(days=2),
    )
    quote = WarrantQuoteSnapshot(
        listing,
        Decimal("2.1"),
        Decimal("2.2"),
        "EUR",
        identity.isin,
        identity.exchange,
        NOW - timedelta(seconds=120),
        isin=identity.isin,
        wkn=identity.wkn,
        venue_mic=identity.mic,
        original_evidence=original_evidence() if original else None,
    )
    result = MarketDataResult(
        quote,
        MarketDataProvider.FRANKFURT_QUOTES,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
        uuid4(),
        NOW - timedelta(seconds=5),
        CacheStatus.MISS,
        QualityStatus.VALID,
        ("Synthetic source warning is not a rule qualification",),
        0,
        0,
        reason_code="SYNTHETIC_RETAINED_ORIGINAL",
    )
    record = SimpleNamespace(
        identity_key=identity.key, payload=RESULT.dump_python(result, mode="json")
    )
    state = SimpleNamespace(suppressed=False)

    @contextmanager
    def no_autoflush():
        state.suppressed = True
        try:
            yield
        finally:
            state.suppressed = False

    async def selected(statement):
        assert state.suppressed
        parameters = statement.compile().params.values()
        assert workspace in parameters and position in parameters
        return selection

    async def saved(_model, key):
        assert state.suppressed
        assert key == (workspace, listing, selection.provider)
        return record

    async def route(_session, request, _provider):
        assert state.suppressed
        assert request.workspace_id == workspace and request.warrant_listing_id == listing
        return identity

    session = SimpleNamespace(
        no_autoflush=no_autoflush(),
        scalar=AsyncMock(side_effect=selected),
        get=AsyncMock(side_effect=saved),
        execute=AsyncMock(side_effect=AssertionError("No fallback, SQL write or lock")),
        flush=AsyncMock(side_effect=AssertionError("No flush")),
        commit=AsyncMock(side_effect=AssertionError("No commit")),
    )
    route_read = AsyncMock(side_effect=route)
    monkeypatch.setattr(risk_read, "read_quote_identity", route_read)
    return SimpleNamespace(
        identity=identity,
        selection=selection,
        record=record,
        result=result,
        session=session,
        no_autoflush=no_autoflush,
        route_read=route_read,
        read_args={
            "workspace_id": workspace,
            "position_id": position,
            "as_of": NOW,
            "expected_warrant_id": warrant,
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("original", [False, True])
async def test_current_saved_quote_preserves_originals_and_has_no_invented_capture_time(
    monkeypatch, original
):
    example = fixture(monkeypatch, original=original)
    before = deepcopy(example.record.payload)
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.quote == example.result.data
    assert evidence.quote.original_evidence == (original_evidence() if original else None)
    assert evidence.route.warrant_id == example.read_args["expected_warrant_id"]
    assert evidence.route.selection_id == example.selection.id
    assert evidence.route.selected_at == example.selection.selected_at
    assert evidence.route.position_id == example.read_args["position_id"]
    assert evidence.route.trading_venue_id == example.identity.trading_venue_id
    assert evidence.provenance.retrieved_at == example.result.retrieved_at
    assert evidence.provenance.warnings == example.result.warnings
    assert evidence.provenance.reason_code == example.result.reason_code
    assert evidence.provenance.quality_status == "VALID"
    assert evidence.provenance.stored_at is None
    assert evidence.provenance.stored_at_status == "NOT_RECORDED_BY_LAST_SUCCESS_STORE"
    assert evidence.provenance.storage_kind == "LAST_SUCCESS"
    assert evidence.provenance.mutable and not evidence.provenance.historical_read
    assert len(evidence.provenance.raw_payload_fingerprint) == 64
    assert example.record.payload == before
    example.session.execute.assert_not_awaited()
    example.session.flush.assert_not_awaited()
    example.session.commit.assert_not_awaited()
    with pytest.raises(FrozenInstanceError):
        evidence.route.warrant_id = uuid4()


@pytest.mark.asyncio
async def test_expected_held_product_cannot_be_replaced_by_same_currency_route(monkeypatch):
    example = fixture(monkeypatch)
    example.read_args["expected_warrant_id"] = uuid4()
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_HELD_INSTRUMENT_MISMATCH"
    assert evidence.quote is None and evidence.route is None and evidence.provenance is None
    example.session.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["workspace_id", "warrant_listing_id", "key"])
async def test_current_route_scope_and_identity_changes_never_read_old_quote(monkeypatch, changed):
    example = fixture(monkeypatch)
    other = "changed-identity" if changed == "key" else uuid4()
    example.route_read.side_effect = None
    example.route_read.return_value = replace(example.identity, **{changed: other})
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_ROUTE_IDENTITY_CHANGED"
    assert evidence.quote is None and evidence.route is None
    example.session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_current_selection_is_not_reconstructed_for_an_earlier_as_of(monkeypatch):
    example = fixture(monkeypatch)
    example.selection.selected_at = NOW + timedelta(seconds=1)
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_SELECTION_AFTER_READ"
    example.session.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_symbol", "DE000ZZ00001"),
        ("isin", "DE000ZZ00001"),
        ("wkn", "ZZ0000"),
        ("currency", "USD"),
        ("provider_exchange_code", "MUND"),
        ("venue_mic", "MUND"),
        ("warrant_listing_id", uuid4()),
    ],
)
async def test_saved_payload_must_match_verified_product_listing_and_venue(
    monkeypatch, field, value
):
    example = fixture(monkeypatch, original=False)
    changed = replace(example.result, data=replace(example.result.data, **{field: value}))
    example.record.payload = RESULT.dump_python(changed, mode="json")
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
    assert evidence.quote is None
    assert evidence.route.identity_key == example.identity.key
    assert evidence.provenance.raw_payload_fingerprint


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong", ["provider", "capability", "quality"])
async def test_saved_envelope_is_not_promoted_despite_parseable_quote(monkeypatch, wrong):
    example = fixture(monkeypatch)
    changes = {
        "provider": MarketDataProvider.GETTEX_DELAYED,
        "capability": MarketDataCapability.HISTORICAL_DAILY_PRICES,
        "quality_status": QualityStatus.SUSPICIOUS,
    }
    field = "quality_status" if wrong == "quality" else wrong
    example.record.payload = RESULT.dump_python(
        replace(example.result, **{field: changes[field]}), mode="json"
    )
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.quote is None
    assert evidence.provenance.warnings == example.result.warnings
    assert evidence.provenance.quality_status == ("SUSPICIOUS" if wrong == "quality" else "VALID")


@pytest.mark.asyncio
async def test_invalid_stored_payload_retains_fingerprint_without_claiming_trusted_values(
    monkeypatch,
):
    example = fixture(monkeypatch)
    example.record.payload = {"data": {"bid": "unparseable"}, "warnings": ["original warning"]}
    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_PAYLOAD_INVALID" and evidence.quote is None
    assert evidence.provenance.raw_payload_fingerprint
    assert evidence.provenance.retrieved_at is None
    assert evidence.provenance.quality_status is None
    assert evidence.provenance.warnings == ()


@pytest.mark.asyncio
async def test_original_source_generation_cannot_follow_saved_retrieval(monkeypatch):
    example = fixture(monkeypatch)
    quote = example.result.data
    changed = replace(
        quote,
        original_evidence=replace(quote.original_evidence, generated_at=NOW),
    )
    example.record.payload = RESULT.dump_python(replace(example.result, data=changed), mode="json")

    evidence = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert evidence.reason == "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
    assert evidence.quote is None
    assert evidence.provenance.retrieved_at == NOW - timedelta(seconds=5)


@pytest.mark.asyncio
async def test_fingerprint_covers_stored_extensions_not_only_normalized_quote(monkeypatch):
    example = fixture(monkeypatch)
    example.record.payload["preserved_extension"] = {"document": "original", "row": 1}
    initial = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    # A fresh context models another snapshot of the mutable last-success. Only
    # an extension ignored by the normalized quote DTO changes in stored JSON.
    example.record.payload["preserved_extension"]["row"] = 2
    example.session.no_autoflush = example.no_autoflush()
    changed = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)

    assert initial.quote == changed.quote
    assert initial.provenance.raw_payload_fingerprint != changed.provenance.raw_payload_fingerprint


def test_explicit_route_metadata_preserves_existing_identity_key_contract():
    workspace, warrant_id, listing_id, venue_id, mapping_id = (UUID(int=i) for i in range(1, 6))
    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace,
        version=7,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        isin="DE000AB00001",
        wkn="AB0000",
    )
    listing = SimpleNamespace(
        id=listing_id,
        workspace_id=workspace,
        warrant_id=warrant_id,
        trading_venue_id=venue_id,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=2,
        quotation_currency_code="EUR",
    )
    venue = SimpleNamespace(id=venue_id, mic="MUND", is_active=True)
    mapping = SimpleNamespace(
        id=mapping_id,
        workspace_id=workspace,
        warrant_listing_id=listing_id,
        provider=MarketDataProvider.GETTEX_DELAYED,
        status=MappingStatus.ACTIVE,
        validated_at=NOW,
        provider_symbol=warrant.isin,
        provider_exchange_code="MUND",
        version=3,
    )
    identity = verified_identity(
        workspace, listing, warrant, venue, MarketDataProvider.GETTEX_DELAYED, mapping
    )

    assert identity.key == "8ad2cf8285654021e943bfc17db58e19b1afb30b4d3598f3f6edc61ef08601ca"
    assert identity.workspace_id == workspace
    assert identity.warrant_id == warrant_id
    assert identity.warrant_listing_id == listing_id
    assert identity.trading_venue_id == venue_id
