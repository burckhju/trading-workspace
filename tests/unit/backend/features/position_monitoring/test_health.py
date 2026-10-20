from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.features.position_monitoring.service.health as health_module
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealthService,
)
from app.features.position_monitoring.service.subjects import (
    MonitoringSubject,
    MonitoringSubjectResolution,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
LISTING_ID = uuid4()
UNDERLYING_ID = uuid4()


class _Session:
    def __init__(self, position_id):
        self._position_id = position_id

    async def scalar(self, _statement):
        return SimpleNamespace(id=self._position_id)

    async def execute(self, _statement):
        return SimpleNamespace(
            first=lambda: (
                SimpleNamespace(id=LISTING_ID, currency_code="EUR"),
                SimpleNamespace(id=UNDERLYING_ID, name="Example basis", isin="US0378331005"),
                SimpleNamespace(mic="XFRA"),
            )
        )


class _Database:
    def __init__(self, position_id):
        self._position_id = position_id

    @asynccontextmanager
    async def session_context(self):
        yield _Session(self._position_id)


class _Reader:
    def __init__(self, resolution):
        self._resolution = resolution

    async def list_resolutions(self):
        return (self._resolution,)


class _Provider:
    def __init__(self, result=None, error: Exception | None = None):
        self._result = result
        self._error = error

    async def get_latest_completed_daily_price(self, _request):
        if self._error is not None:
            raise self._error
        return self._result


def _subject(position_id, trade_id):
    return MonitoringSubject(
        workspace_id=uuid4(),
        position_id=position_id,
        trade_id=trade_id,
        listing_id=LISTING_ID,
        mapping_id=uuid4(),
        symbol="DAX.INDX",
        rules=(),
    )


def _daily_result(*, trading_date: date, quality: QualityStatus = QualityStatus.VALID):
    price = DailyPrice(
        listing_id=LISTING_ID,
        trading_date=trading_date,
        open=Decimal("24000"),
        high=Decimal("24200"),
        low=Decimal("23900"),
        close=Decimal("24100"),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="DAX.INDX",
        retrieved_at=NOW,
        source_updated_at=NOW,
        quality_status=quality,
    )
    return MarketDataResult(
        data=price,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.LATEST_COMPLETED_DAILY_PRICE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.HIT,
        quality_status=quality,
        warnings=(),
        retry_count=0,
        provider_call_cost=0,
    )


def _missing_result():
    return MarketDataResult(
        data=None,
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.LATEST_COMPLETED_DAILY_PRICE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.HIT,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=0,
    )


async def _health(monkeypatch, provider):
    trade_id = uuid4()
    position_id = uuid4()
    resolution = MonitoringSubjectResolution(
        position_id=position_id,
        subject=_subject(position_id, trade_id),
    )
    monkeypatch.setattr(
        health_module,
        "SqlAlchemyMonitoringSubjectReader",
        lambda _session: _Reader(resolution),
    )
    service = PositionMonitoringHealthService(
        database=_Database(position_id),
        market_data=provider,
        max_completed_price_age_days=4,
        now=lambda: NOW,
    )
    return await service.for_trade(trade_id)


@pytest.mark.asyncio
async def test_health_reports_current_completed_daily_data(monkeypatch) -> None:
    result = await _health(
        monkeypatch,
        _Provider(_daily_result(trading_date=date(2026, 9, 5))),
    )

    assert result is not None
    assert result.status is MonitoringHealthStatus.OK
    assert result.age_days == 1
    assert result.symbol == "DAX.INDX"
    assert result.basis.listing_id == LISTING_ID
    assert result.basis.venue_mic == "XFRA"
    assert result.basis.underlying_id == UNDERLYING_ID
    assert result.daily_price.close == Decimal("24100")
    assert result.daily_price.low == Decimal("23900")
    assert result.daily_price.high == Decimal("24200")
    assert result.daily_price.retrieved_at == NOW


@pytest.mark.asyncio
async def test_health_reports_stale_without_turning_it_into_trading_alert(monkeypatch) -> None:
    result = await _health(
        monkeypatch,
        _Provider(_daily_result(trading_date=date(2026, 9, 1))),
    )

    assert result is not None
    assert result.status is MonitoringHealthStatus.STALE
    assert result.reason == "COMPLETED_DAILY_PRICE_STALE"
    assert result.age_days == 5
    assert result.daily_price.close == Decimal("24100")


@pytest.mark.asyncio
async def test_health_reports_missing_market_data(monkeypatch) -> None:
    result = await _health(monkeypatch, _Provider(_missing_result()))

    assert result is not None
    assert result.status is MonitoringHealthStatus.MISSING
    assert result.reason == "NO_COMPLETED_DAILY_PRICE"


@pytest.mark.asyncio
async def test_health_reports_provider_failure_as_data_error(monkeypatch) -> None:
    result = await _health(monkeypatch, _Provider(error=RuntimeError("provider down")))

    assert result is not None
    assert result.status is MonitoringHealthStatus.ERROR
    assert result.reason == "MARKET_DATA_REQUEST_FAILED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "problem,reason",
    [
        ("listing", "MARKET_DATA_IDENTITY_MISMATCH"),
        ("currency", "MARKET_DATA_IDENTITY_MISMATCH"),
        ("future", "DAILY_PRICE_IN_FUTURE"),
        ("quality", "MARKET_DATA_QUALITY_SUSPICIOUS"),
    ],
)
async def test_does_not_attach_an_invalid_price_to_the_selected_basis(monkeypatch, problem, reason):
    daily = _daily_result(trading_date=date(2026, 9, 5))
    changes = {
        "listing": {"listing_id": uuid4()},
        "currency": {"currency": "USD"},
        "future": {"trading_date": date(2026, 9, 7)},
        "quality": {"quality_status": QualityStatus.SUSPICIOUS},
    }
    result = await _health(
        monkeypatch, _Provider(replace(daily, data=replace(daily.data, **changes[problem])))
    )
    assert result.status is MonitoringHealthStatus.ERROR
    assert result.reason == reason
    assert result.daily_price is None
    assert result.basis.venue_mic == "XFRA"


@pytest.mark.asyncio
async def test_provider_disabled_preserves_selected_basis(monkeypatch):
    result = await _health(monkeypatch, None)
    assert result.reason == "MARKET_DATA_PROVIDER_UNAVAILABLE"
    assert result.basis.listing_id == LISTING_ID
    assert result.daily_price is None
