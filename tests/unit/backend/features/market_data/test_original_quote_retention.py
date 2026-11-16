"""Disposable SQLite round trips of actual retention and sampled original evidence."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_tests
from tests.unit.backend.features.market_data.test_original_quote_evidence import evidence
from tests.unit.backend.features.market_data.test_retained_quotes import NOW, SqlDatabase
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import (
    context as adapter_context,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import payload

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.quote_history import POLICY, QUOTE, QuoteHistoryReader
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot

context = retained_tests.context


def runtime(c, at, provider=None):
    return RetainedWarrantQuoteProvider(
        c.database,
        provider or c.provider,
        MarketDataProvider.FRANKFURT_QUOTES,
        capture_clock=lambda: at,
    )


@pytest.mark.asyncio
async def test_real_adapter_retention_and_restart_keep_original_proof_and_result_provenance(
    context,
):
    c = context
    with Session(c.database.engine) as session:
        session.get(WarrantProviderMappingModel, c.mapping).provider_exchange_code = "XFRA"
        session.commit()
    data = payload()
    data["generated_at"] = NOW.isoformat()
    data["records"][0].update(bid_at="2026-09-11T20:00:00+02:00", ask_at="2026-09-11T17:59:50Z")
    adapter, _database, snapshots, _request, _row = adapter_context()
    adapter._database = c.database
    adapter._clock = lambda: NOW
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(data), NOW, False)
    first = await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    proof = first.data.original_evidence
    assert proof.bid.observed_at == NOW
    assert first.data.observed_at == proof.ask.observed_at == NOW - timedelta(seconds=10)
    with Session(c.database.engine) as session:
        sample = session.scalar(select(WarrantQuoteSampleModel))
        original_sample = deepcopy(sample.payload)
        original_id, original_fingerprint = sample.id, sample.quote_fingerprint
        assert original_sample["quality_status"] == first.quality_status.value == "VALID"
        assert original_sample["warnings"] == list(first.warnings)
        assert original_sample["reason_code"] == first.reason_code
        assert original_sample["quote"]["original_evidence"]["source_reference"] == data["source"]
        assert original_sample["quote"]["original_evidence"]["bid"]["original_time_text"] == (
            "2026-09-11T20:00:00+02:00"
        )
        retained = session.scalar(select(WarrantQuoteObservationModel))
        assert (
            retained.payload["data"]["original_evidence"]
            == original_sample["quote"]["original_evidence"]
        )
    c.database.engine.dispose()
    c.database = SqlDatabase(c.url)
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError("synthetic failure")
    fallback = await runtime(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    assert fallback.data.retained is True
    assert fallback.data.original_evidence == proof
    assert fallback.data.observed_at == first.data.observed_at
    assert fallback.retrieved_at == first.retrieved_at
    async with c.database.session_context() as session:
        report = await QuoteHistoryReader(session).report(
            c.request.workspace_id, c.warrant, now=NOW + timedelta(minutes=5)
        )
    original = next(item for item in report.items if item.id == original_id)
    assert original.quote.original_evidence == proof
    assert original.quote_fingerprint == original_fingerprint
    with Session(c.database.engine) as session:
        assert session.get(WarrantQuoteSampleModel, original_id).payload == original_sample
    assert report.items[0].quote is None
    snapshots.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_new_capture_keeps_legacy_quote_hash_and_never_rewrites_legacy_payload(context):
    c = context
    async with c.database.session_context() as session:
        identity = await read_quote_identity(
            session, c.request, MarketDataProvider.FRANKFURT_QUOTES
        )
    legacy_quote = QUOTE.dump_python(c.result.data, mode="json")
    legacy_quote.pop("original_evidence")
    legacy_quote.pop("original_market_status")
    # This is the released pre-extension fingerprint format and stored payload.
    legacy_material = {
        key: value
        for key, value in legacy_quote.items()
        if key not in {"assessed_at", "retained", "refresh_error"}
    }
    legacy_fingerprint = hashlib.sha256(
        json.dumps([identity.key, legacy_material], sort_keys=True).encode()
    ).hexdigest()
    legacy_payload = {
        "quote": legacy_quote,
        "retrieved_at": NOW.isoformat(),
        "cache_status": c.result.cache_status.value,
        "policy_version": POLICY,
    }
    original_id = uuid4()
    with Session(c.database.engine) as session:
        session.add(
            WarrantQuoteSampleModel(
                id=original_id,
                workspace_id=c.request.workspace_id,
                warrant_id=c.warrant,
                warrant_listing_id=c.request.warrant_listing_id,
                provider="FRANKFURT_QUOTES",
                identity_key=identity.key,
                isin=identity.isin,
                slot_at=NOW,
                day_utc=NOW.date(),
                captured_at=NOW,
                status="REFERENCE_ONLY",
                reason=None,
                quote_fingerprint=legacy_fingerprint,
                payload=legacy_payload,
            )
        )
        session.commit()
    await runtime(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        rows = session.scalars(select(WarrantQuoteSampleModel)).all()
        assert len(rows) == 2
        assert {row.quote_fingerprint for row in rows} == {legacy_fingerprint}
        assert session.get(WarrantQuoteSampleModel, original_id).payload == legacy_payload
        new = next(row for row in rows if row.id != original_id)
        assert "original_evidence" not in new.payload["quote"]
        assert new.payload["quality_status"] == "VALID"
        assert new.payload["warnings"] == []
        assert new.payload["reason_code"] is None
    async with c.database.session_context() as session:
        report = await QuoteHistoryReader(session).report(
            c.request.workspace_id, c.warrant, now=NOW + timedelta(minutes=5)
        )
    assert report.segments[0].distinct_quote_evidence == 1
    assert all(item.quote.original_evidence is None for item in report.items)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["bid_clock", "source", "generated_at"])
async def test_real_original_clock_or_source_change_creates_distinct_sample_proof(context, change):
    c = context
    proof = evidence()
    with Session(c.database.engine) as session:
        session.get(WarrantProviderMappingModel, c.mapping).provider_exchange_code = "XFRA"
        session.commit()
    quote = replace(
        c.result.data,
        bid=proof.bid.price,
        ask=proof.ask.price,
        reference_price=None,
        reference_price_type=None,
        provider_exchange_code="XFRA",
        source_mode="FRANKFURT_REALTIME_MONITORING",
        observed_at=proof.ask.observed_at,
        original_evidence=proof,
    )
    c.provider.get_warrant_listing_quote.return_value = replace(c.result, data=quote)
    await runtime(c, NOW).get_warrant_listing_quote(c.request)
    if change == "bid_clock":
        proof = replace(
            proof,
            bid=replace(
                proof.bid,
                observed_at=NOW - timedelta(seconds=1),
                original_time_text="2026-09-11T17:59:59Z",
            ),
        )
    elif change == "source":
        proof = replace(proof, source_reference="other-synthetic-source")
    else:
        proof = replace(proof, generated_at=NOW + timedelta(seconds=1))
    c.provider.get_warrant_listing_quote.return_value = replace(
        c.result,
        retrieved_at=NOW + timedelta(seconds=1),
        data=replace(quote, original_evidence=proof, assessed_at=NOW + timedelta(seconds=1)),
    )
    await runtime(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        rows = session.scalars(select(WarrantQuoteSampleModel)).all()
        assert len(rows) == 2
        assert len({row.quote_fingerprint for row in rows}) == 2
        assert all(
            row.payload["quote"]["observed_at"]
            == quote.observed_at.isoformat().replace("+00:00", "Z")
            for row in rows
        )


@pytest.mark.asyncio
async def test_capture_diagnostics_do_not_create_a_new_original_quote(context):
    c = context
    await runtime(c, NOW).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.return_value = replace(
        c.result,
        warnings=("synthetic refreshed diagnostic",),
        reason_code="SYNTHETIC_DIAGNOSTIC",
        retrieved_at=NOW + timedelta(minutes=5),
        data=replace(c.result.data, assessed_at=NOW + timedelta(minutes=5)),
    )
    await runtime(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        rows = session.scalars(
            select(WarrantQuoteSampleModel).order_by(WarrantQuoteSampleModel.captured_at)
        ).all()
        assert len({row.quote_fingerprint for row in rows}) == 1
        assert rows[0].payload["warnings"] == []
        assert rows[1].payload["warnings"] == ["synthetic refreshed diagnostic"]
        assert rows[1].payload["reason_code"] == "SYNTHETIC_DIAGNOSTIC"
