from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.domain.models import MonitoringRule, MonitoringRuleType
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service.application import MonitoringEvaluationResult
from app.features.position_monitoring.service.cycle import PositionMonitoringCycleService
from app.features.position_monitoring.service.subjects import (
    MonitoringSubject,
    MonitoringSubjectResolution,
)


class Subjects:
    def __init__(self, values: tuple[MonitoringSubjectResolution, ...]) -> None:
        self.values = values

    async def list_resolutions(self) -> tuple[MonitoringSubjectResolution, ...]:
        return self.values


class MarketData:
    def __init__(self, price: DailyPrice | None) -> None:
        self.price = price

    async def get_latest_completed_daily_price(self, request: object) -> MarketDataResult[DailyPrice | None]:
        return MarketDataResult(
            data=self.price,
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.LATEST_COMPLETED_DAILY_PRICE,
            correlation_id=uuid4(),
            retrieved_at=datetime(2026, 9, 3, 8, tzinfo=UTC),
            cache_status=CacheStatus.MISS,
            quality_status=QualityStatus.VALID,
            warnings=(),
            retry_count=0,
            provider_call_cost=1,
        )


class Processor:
    def __init__(self) -> None:
        self.calls = 0

    async def process(self, **kwargs: object) -> MonitoringEvaluationResult:
        self.calls += 1
        return MonitoringEvaluationResult(TriggerTransition.STAYED_CLEAR, None)


def subject() -> MonitoringSubject:
    return MonitoringSubject(
        workspace_id=uuid4(),
        position_id=uuid4(),
        trade_id=uuid4(),
        listing_id=uuid4(),
        mapping_id=uuid4(),
        symbol="SAP",
        rules=(MonitoringRule("stop", MonitoringRuleType.STOP_REACHED, Decimal("100")),),
    )


def price(*, trading_date: date) -> DailyPrice:
    return DailyPrice(
        listing_id=uuid4(),
        trading_date=trading_date,
        open=Decimal("105"),
        high=Decimal("110"),
        low=Decimal("99"),
        close=Decimal("106"),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="SAP",
        retrieved_at=datetime(2026, 9, 3, 8, tzinfo=UTC),
        source_updated_at=None,
        quality_status=QualityStatus.VALID,
    )


@pytest.mark.asyncio
async def test_missing_and_stale_market_data_do_not_become_trading_alerts() -> None:
    item = subject()
    resolutions = (MonitoringSubjectResolution(item.position_id, item),)
    processor = Processor()
    missing = PositionMonitoringCycleService(
        subjects=Subjects(resolutions),
        market_data=MarketData(None),
        processor=processor,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
        new_id=uuid4,
    )
    missing_result = await missing.run()
    assert missing_result.missing_market_data == 1
    assert missing_result.alerts_created == 0

    stale = PositionMonitoringCycleService(
        subjects=Subjects(resolutions),
        market_data=MarketData(price(trading_date=date(2026, 8, 20))),
        processor=processor,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
        new_id=uuid4,
    )
    stale_result = await stale.run()
    assert stale_result.stale_market_data == 1
    assert stale_result.alerts_created == 0
    assert processor.calls == 0
