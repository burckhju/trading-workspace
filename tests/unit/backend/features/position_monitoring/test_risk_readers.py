"""Provenance qualification remains separate from numerical signals."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import TypeAdapter

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.types import MarketDataResult

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,reason",
    [
        ("good", "LAST_SUCCESS_IS_NOT_A_PRICE_SERIES"),
        ("no_selection", "NO_CONFIRMED_SAVED_QUOTE_SOURCE"),
        ("unknown_provider", "SAVED_QUOTE_PROVIDER_UNSUPPORTED"),
        ("identity", "SAVED_QUOTE_ROUTE_IDENTITY_CHANGED"),
        ("no_saved", "NO_SAVED_QUOTE_FOR_CURRENT_ROUTE"),
        ("invalid_payload", "SAVED_QUOTE_PAYLOAD_INVALID"),
        ("no_data", "SAVED_QUOTE_QUALITY_INVALID"),
        ("currency", "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"),
        ("future_original", "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"),
        ("future_receipt", "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"),
    ],
)
async def test_saved_quote_reader_requires_current_route_and_preserves_original_time(
    case, reason, monkeypatch
):
    import app.features.market_data.service.risk_read as module

    listing = uuid4()
    selection = SimpleNamespace(
        selection_status="SELECTED",
        warrant_listing_id=listing,
        provider="JPMORGAN",
        identity_key="current",
    )
    identity = SimpleNamespace(key="current", isin="DE000SYN0010", currency="EUR")
    quote = WarrantQuoteSnapshot(
        listing,
        Decimal(2),
        None,
        "EUR",
        "DE000SYN0010",
        "ISSUER",
        None,
        isin="DE000SYN0010",
        source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
    )
    result = MarketDataResult(
        quote,
        MarketDataProvider.JPMORGAN,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
        uuid4(),
        NOW,
        CacheStatus.MISS,
        QualityStatus.VALID,
        (),
        0,
        0,
    )
    if case == "unknown_provider":
        selection.provider = "NOT_A_PROVIDER"
    if case == "identity":
        identity.key = "superseded"
    if case == "no_data":
        result = replace(result, data=None)
    if case == "currency":
        result = replace(result, data=replace(quote, currency="USD"))
    if case == "future_original":
        result = replace(
            result,
            data=replace(
                quote,
                observed_at=NOW + timedelta(seconds=1),
                quote_time_basis=None,
                source_mode=None,
            ),
        )
    if case == "future_receipt":
        result = replace(result, retrieved_at=NOW + timedelta(seconds=1))
    payload = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None]).dump_python(
        result, mode="json"
    )
    record = SimpleNamespace(
        identity_key="current", payload={} if case == "invalid_payload" else payload
    )
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None if case == "no_selection" else selection),
        get=AsyncMock(return_value=None if case == "no_saved" else record),
    )
    monkeypatch.setattr(module, "read_quote_identity", AsyncMock(return_value=identity))
    evidence = await RiskMarketDataReader(session).saved_quote(
        workspace_id=uuid4(), position_id=uuid4(), as_of=NOW
    )
    assert evidence.reason == reason
    if case == "good":
        assert evidence.quote.observed_at is None and evidence.retrieved_at == NOW
        assert evidence.history_observations == 1
        assert evidence.refresh_status == "LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER"
    else:
        assert evidence.quote is None
