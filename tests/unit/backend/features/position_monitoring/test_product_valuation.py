from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
    ProductValuationStatus,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
monitoring_api = import_module("app.features.position_monitoring.api.router")


class _ExecuteResult:
    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *, trade, position, evaluation=None, listing=None):
        self._trade = trade
        self._position = position
        self._scalars = [evaluation, listing]

    async def execute(self, _statement):
        return _ExecuteResult((self._trade, self._position))

    async def scalar(self, _statement):
        return self._scalars.pop(0)


class _Database:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def session_context(self):
        yield self._session


class _Provider:
    def __init__(self, result):
        self._result = result

    async def get_warrant_listing_quote(self, _request):
        return self._result


def _context(*, external: bool = False):
    trade_id = uuid4()
    position_id = uuid4()
    evaluation_id = None if external else uuid4()
    listing_id = uuid4()
    trade = SimpleNamespace(
        id=trade_id,
        workspace_id=uuid4(),
        product_evaluation_id=evaluation_id,
    )
    position = SimpleNamespace(
        id=position_id,
        open_quantity=10,
        cost_basis=Decimal("20.00"),
    )
    evaluation = (
        None if external else SimpleNamespace(id=evaluation_id, warrant_listing_id=listing_id)
    )
    listing = SimpleNamespace(
        id=listing_id,
        symbol="TEST12.STU",
        quotation_currency_code="EUR",
    )
    return trade, position, evaluation, listing


def _quote_result(
    *,
    listing_id,
    bid=Decimal("2.50"),
    ask=Decimal("2.55"),
    currency="EUR",
    observed_at=NOW,
    retrieved_at=NOW,
    trading_status=None,
    source_mode=None,
):
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=listing_id,
        bid=bid,
        ask=ask,
        currency=currency,
        provider_symbol="TEST12",
        provider_exchange_code="STU",
        observed_at=observed_at,
        trading_status=trading_status,
        source_mode=source_mode,
    )
    return MarketDataResult(
        data=quote,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=retrieved_at,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )


@pytest.mark.asyncio
async def test_values_open_long_position_at_exact_listing_bid() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=listing.id))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.AVAILABLE
    assert result.warrant_listing_id == listing.id
    assert result.bid == Decimal("2.50")
    assert result.quote_age_seconds == 0
    assert result.max_quote_age_seconds == 3600
    assert result.market_value == Decimal("25.00")
    assert result.unrealized_gross_pnl == Decimal("5.00")
    assert result.analysis_usable is True
    assert result.analysis_warning is None
    assert result.analysis_market_value == Decimal("25.00")
    assert result.analysis_unrealized_gross_pnl == Decimal("5.00")


@pytest.mark.asyncio
async def test_stale_quote_does_not_create_current_market_value_or_unrealized_pnl() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(
        _quote_result(
            listing_id=listing.id,
            observed_at=NOW - timedelta(hours=2),
            retrieved_at=NOW,
        )
    )
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
        max_quote_age_seconds=3600,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.STALE
    assert result.reason == "WARRANT_QUOTE_STALE"
    assert result.bid == Decimal("2.50")
    assert result.quote_age_seconds == 7200
    assert result.max_quote_age_seconds == 3600
    assert result.market_value is None
    assert result.unrealized_gross_pnl is None
    assert result.valuation_usable is False
    assert result.execution_usable is False
    assert result.analysis_usable is True
    assert result.analysis_warning == "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"
    assert result.analysis_market_value == Decimal("25.00")
    assert result.analysis_unrealized_gross_pnl == Decimal("5.00")
    assert result.quote_observed_at == NOW - timedelta(hours=2)
    assert result.provider_identity == "TEST12"


@pytest.mark.asyncio
async def test_previous_close_is_usable_for_indicative_weekend_valuation_only() -> None:
    trade, position, evaluation, listing = _context()
    friday_close = datetime(2026, 9, 11, 19, 59, 13, tzinfo=UTC)
    saturday = datetime(2026, 9, 12, 6, 51, 13, tzinfo=UTC)
    provider = _Provider(
        _quote_result(
            listing_id=listing.id,
            observed_at=friday_close,
            retrieved_at=saturday,
            trading_status="CLOSED",
            source_mode="OFFICIAL_ISSUER_INDICATION",
        )
    )
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
        max_quote_age_seconds=3600,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.LAST_AVAILABLE
    assert result.reason == "MARKET_CLOSED_LAST_AVAILABLE_QUOTE"
    assert result.provenance_listing_id == listing.id
    assert result.quote_listing_id == listing.id
    assert result.market_value == Decimal("25.00")
    assert result.unrealized_gross_pnl == Decimal("5.00")
    assert result.valuation_usable is True
    assert result.execution_usable is False
    assert result.freshness_policy == "DE_WARRANT_SESSION_FRESHNESS_V1"
    assert result.analysis_usable is True
    assert result.analysis_warning == "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"
    assert result.analysis_market_value == result.market_value
    assert result.analysis_unrealized_gross_pnl == result.unrealized_gross_pnl


@pytest.mark.asyncio
async def test_external_trade_without_listing_provenance_is_not_guessed() -> None:
    trade, position, _evaluation, _listing = _context(external=True)
    service = ProductPositionValuationService(
        database=_Database(_Session(trade=trade, position=position)),
        quote_provider=None,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.UNAVAILABLE
    assert result.reason == "WARRANT_LISTING_PROVENANCE_UNAVAILABLE"
    assert result.market_value is None


@pytest.mark.asyncio
async def test_missing_bid_does_not_create_indicative_value() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=listing.id, bid=None))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.MISSING
    assert result.reason == "WARRANT_BID_MISSING"
    assert result.market_value is None
    assert result.unrealized_gross_pnl is None


@pytest.mark.asyncio
async def test_wrong_quote_listing_is_rejected() -> None:
    trade, position, evaluation, listing = _context()
    provider = _Provider(_quote_result(listing_id=uuid4()))
    service = ProductPositionValuationService(
        database=_Database(
            _Session(
                trade=trade,
                position=position,
                evaluation=evaluation,
                listing=listing,
            )
        ),
        quote_provider=provider,
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.status is ProductValuationStatus.ERROR
    assert result.reason == "WARRANT_QUOTE_LISTING_MISMATCH"
    assert result.market_value is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "quote_changes",
    [
        {"bid": None},
        {"currency": "USD"},
        {"listing_id": uuid4()},
        {"observed_at": NOW + timedelta(minutes=1)},
    ],
)
async def test_analysis_does_not_relax_identity_price_currency_or_time_gates(quote_changes):
    trade, position, evaluation, listing = _context()
    fields = {"listing_id": listing.id, **quote_changes}
    service = ProductPositionValuationService(
        database=_Database(
            _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        ),
        quote_provider=_Provider(_quote_result(**fields)),
    )

    result = await service.for_trade(trade.id)

    assert result is not None
    assert result.analysis_usable is False
    assert result.analysis_warning is None
    assert result.analysis_market_value is None
    assert result.analysis_unrealized_gross_pnl is None
    assert result.execution_usable is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("age", "trading_status", "expected_status", "analysis_usable", "warning"),
    [
        (0, "OPEN", "AVAILABLE", True, None),
        (7200, "OPEN", "STALE", True, "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"),
        (7200, "CLOSED", "LAST_AVAILABLE", True, "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"),
        (-60, "OPEN", "ERROR", False, None),
    ],
)
async def test_api_retains_analysis_permission_warning_and_quote_provenance(
    monkeypatch, age, trading_status, expected_status, analysis_usable, warning
):
    trade, position, evaluation, listing = _context()
    observed_at = datetime(2026, 9, 11, 19, 59, 13, tzinfo=UTC)
    service = ProductPositionValuationService(
        database=_Database(
            _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        ),
        quote_provider=_Provider(
            _quote_result(
                listing_id=listing.id,
                observed_at=observed_at,
                retrieved_at=observed_at + timedelta(seconds=age),
                trading_status=trading_status,
                source_mode="OFFICIAL_ISSUER_INDICATION",
            )
        ),
    )
    monkeypatch.setattr(monitoring_api, "ProductPositionValuationService", lambda **_: service)
    monkeypatch.setattr(monitoring_api, "build_warrant_quote_resolver", lambda _: None)

    response = await monitoring_api.get_trade_product_valuation(
        trade.id, SimpleNamespace(database=None)
    )
    payload = response.model_dump(mode="json")

    assert payload["status"] == expected_status
    assert payload["analysis_usable"] is analysis_usable
    assert payload["analysis_warning"] == warning
    assert payload["analysis_market_value"] == ("25.00" if analysis_usable else None)
    assert payload["analysis_unrealized_gross_pnl"] == ("5.00" if analysis_usable else None)
    assert payload["execution_usable"] is False
    assert payload["quote_observed_at"] == "2026-09-11T19:59:13Z"
    assert payload["provider_identity"] == "TEST12"
    assert payload["quote_listing_id"] == str(listing.id)
    assert payload["provenance_listing_id"] == str(listing.id)
