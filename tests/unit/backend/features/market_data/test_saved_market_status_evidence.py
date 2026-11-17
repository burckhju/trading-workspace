"""Passive saved-quote reads bind status points but never recover a latest-status stream."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

import pytest
from tests.unit.backend.features.market_data.test_saved_quote_evidence import (
    NOW,
    RESULT,
    fixture,
)

from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.service.risk_read import RiskMarketDataReader


def status_fixture(monkeypatch):
    example = fixture(monkeypatch)
    original = example.result.data.original_evidence
    status = OriginalMarketStatusEvidence(
        version="original-market-status-evidence-v1",
        source_contract=original.source_contract,
        source_reference=original.source_reference,
        generated_at=original.generated_at,
        isin=original.isin,
        venue_mic=original.venue_mic,
        status="OPEN",
        original_status_text="OPEN",
        source_status_field="trading_status",
        observed_at=NOW - timedelta(seconds=30),
        original_time_text="2026-11-15T10:59:30+01:00",
        source_time_field="status_observed_at",
    )
    example.result = replace(
        example.result,
        data=replace(example.result.data, trading_status="OPEN", original_market_status=status),
    )
    example.record.payload = RESULT.dump_python(example.result, mode="json")
    return example


@pytest.mark.asyncio
async def test_saved_status_has_unchanged_source_point_and_explicit_last_success_only_provenance(
    monkeypatch,
):
    example = status_fixture(monkeypatch)
    before = deepcopy(example.record.payload)
    saved = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)
    assert saved.quote.original_market_status == example.result.data.original_market_status
    assert saved.quote.original_market_status.observed_at == NOW - timedelta(seconds=30)
    assert saved.quote.original_market_status.original_time_text == "2026-11-15T10:59:30+01:00"
    assert saved.refresh_status == "LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER"
    assert saved.provenance.storage_kind == "LAST_SUCCESS"
    assert saved.provenance.stored_at is None
    assert saved.provenance.mutable and not saved.provenance.historical_read
    assert example.record.payload == before
    example.session.execute.assert_not_awaited()
    example.session.flush.assert_not_awaited()
    example.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_source_generation_after_retrieval_is_not_accepted(monkeypatch):
    example = status_fixture(monkeypatch)
    quote = example.result.data
    changed = replace(
        quote,
        original_evidence=None,
        original_market_status=replace(quote.original_market_status, generated_at=NOW),
    )
    example.record.payload = RESULT.dump_python(replace(example.result, data=changed), mode="json")
    saved = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)
    assert saved.quote is None
    assert saved.reason == "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
    assert saved.provenance.retrieved_at == example.result.retrieved_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("isin", "DE000VH7S657"),
        ("venue_mic", "XSTU"),
        ("status", "SUSPENDED"),
        ("source_contract", "other-contract"),
        ("source_reference", "other-source"),
        ("generated_at", "2026-11-15T09:59:59Z"),
        ("original_time_text", "2026-11-15T10:59:31+01:00"),
    ],
)
async def test_inconsistent_stored_status_is_not_silently_dropped(monkeypatch, field, value):
    example = status_fixture(monkeypatch)
    example.record.payload["data"]["original_market_status"][field] = value
    saved = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)
    assert saved.quote is None
    assert saved.reason == "SAVED_QUOTE_PAYLOAD_INVALID"
    assert saved.provenance.raw_payload_fingerprint


@pytest.mark.asyncio
async def test_changed_original_status_changes_payload_fingerprint_even_when_price_is_unchanged(
    monkeypatch,
):
    example = status_fixture(monkeypatch)
    first = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)
    quote = example.result.data
    changed = replace(
        quote,
        trading_status="CLOSED",
        original_market_status=replace(
            quote.original_market_status, status="CLOSED", original_status_text="CLOSED"
        ),
    )
    example.record.payload = RESULT.dump_python(replace(example.result, data=changed), mode="json")
    example.session.no_autoflush = example.no_autoflush()
    closed = await RiskMarketDataReader(example.session).saved_quote(**example.read_args)
    assert first.quote.bid == closed.quote.bid
    assert first.quote.observed_at == closed.quote.observed_at
    assert closed.quote.original_market_status.status == "CLOSED"
    assert first.provenance.raw_payload_fingerprint != closed.provenance.raw_payload_fingerprint
