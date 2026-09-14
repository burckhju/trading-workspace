"""Obtain a price for the user's confirmed rule identity, without cross-instrument fallback."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.market_data.service.types import LatestDailyPriceRequest
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.service.product_valuation import ProductPositionValuation
from app.features.position_monitoring.service.subjects import MonitoringSubject
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding


class ProductValuationReader(Protocol):
    async def for_trade(self, trade_id: UUID) -> ProductPositionValuation | None: ...


@dataclass(frozen=True, slots=True)
class RulePriceResult:
    status: str
    reason: str
    observation: PriceObservation | None = None


async def rule_price(
    *,
    subject: MonitoringSubject,
    rule: MonitoringRule,
    market_data: LatestCompletedDailyPriceProvider | None,
    products: ProductValuationReader | None,
    now: datetime,
    max_age_days: int,
) -> RulePriceResult:
    binding = rule.price_binding
    if binding is None:
        return RulePriceResult("BLOCKED", "RULE_PRICE_BASIS_UNCONFIRMED")
    expected = subject.warrant_id if binding.basis is PriceBasis.WARRANT else subject.underlying_id
    if expected is None or expected != binding.instrument_id:
        return RulePriceResult("BLOCKED", "RULE_INSTRUMENT_MISMATCH")
    if binding.basis is PriceBasis.WARRANT:
        if products is None:
            return RulePriceResult("MISSING", "WARRANT_QUOTE_PROVIDER_UNAVAILABLE")
        value = await products.for_trade(subject.trade_id)
        if value is None or not value.monitoring_usable or value.reference_price is None:
            return RulePriceResult("MISSING", value.reason if value else "NO_USABLE_WARRANT_QUOTE")
        if (
            value.trade_id != subject.trade_id
            or value.position_id != subject.position_id
            or value.isin != subject.warrant_isin
            or value.currency != binding.currency
            or value.quote_listing_id is None
            or not value.provider_identity
            or not value.selected_source
        ):
            return RulePriceResult("BLOCKED", "WARRANT_QUOTE_IDENTITY_OR_CURRENCY_MISMATCH")
        if value.quote_observed_at is None or value.quote_observed_at > now:
            return RulePriceResult("ERROR", "INVALID_QUOTE_TIMESTAMP")
        # Never promote Last/Close to Bid, nor indicative monitoring to execution permission.
        warning = value.analysis_warning or (
            "INDICATIVE_REFERENCE_PRICE" if value.reference_price_type != "BID" else None
        )
        context = {
            "price_type": value.reference_price_type,
            "provider": value.selected_source,
            "provider_identity": value.provider_identity,
            "isin": value.isin,
            "listing_id": str(value.quote_listing_id),
            "venue_mic": value.quote_venue_mic,
            "source_mode": value.source_mode,
            "trading_status": value.trading_status,
            "delay_seconds": (
                str(value.quote_delay_seconds) if value.quote_delay_seconds is not None else None
            ),
            "observed_at": value.quote_observed_at.isoformat(),
            "retrieved_at": (
                value.quote_retrieved_at.isoformat() if value.quote_retrieved_at else None
            ),
            "warning": warning,
            "refresh_error": value.quote_refresh_error,
            "execution_usable": "false",
        }
        return RulePriceResult(
            "INDICATIVE" if warning else "AVAILABLE",
            "WARRANT_REFERENCE_PRICE_CHECKED",
            PriceObservation(value.reference_price, value.quote_observed_at, binding, context),
        )

    if subject.listing_id is None or subject.mapping_id is None:
        return RulePriceResult("BLOCKED", "NO_ACTIVE_UNDERLYING_MAPPING")
    if binding.currency != subject.listing_currency:
        return RulePriceResult("BLOCKED", "RULE_CURRENCY_MISMATCH")
    if market_data is None:
        return RulePriceResult("MISSING", "UNDERLYING_PROVIDER_UNAVAILABLE")
    result = await market_data.get_latest_completed_daily_price(
        LatestDailyPriceRequest(
            workspace_id=subject.workspace_id,
            listing_id=subject.listing_id,
            mapping_id=subject.mapping_id,
            correlation_id=uuid4(),
            as_of_date=now.date() - timedelta(days=1),
        )
    )
    price = result.data
    if price is None:
        return RulePriceResult("MISSING", "NO_COMPLETED_DAILY_PRICE")
    if price.listing_id != subject.listing_id or price.currency != binding.currency:
        return RulePriceResult("BLOCKED", "UNDERLYING_PRICE_IDENTITY_OR_CURRENCY_MISMATCH")
    if (
        result.quality_status is not QualityStatus.VALID
        or price.quality_status is not QualityStatus.VALID
    ):
        return RulePriceResult("ERROR", "INVALID_DAILY_PRICE_QUALITY")
    if price.trading_date >= now.date():
        return RulePriceResult("ERROR", "DAILY_SESSION_NOT_COMPLETED")
    if (now.date() - price.trading_date).days > max_age_days:
        return RulePriceResult("STALE", "COMPLETED_DAILY_PRICE_STALE")
    observed_at = price.source_updated_at or price.retrieved_at
    if observed_at > now or price.retrieved_at > now:
        return RulePriceResult("ERROR", "INVALID_QUOTE_TIMESTAMP")
    stop = rule.rule_type is MonitoringRuleType.STOP_REACHED
    return RulePriceResult(
        "AVAILABLE",
        "COMPLETED_UNDERLYING_DAILY_PRICE_CHECKED",
        PriceObservation(
            price.low if stop else price.high,
            observed_at,
            PriceBinding(PriceBasis.UNDERLYING, expected, price.currency),
            {
                "price_type": "DAILY_LOW" if stop else "DAILY_HIGH",
                "trading_date": price.trading_date.isoformat(),
                "provider": price.provider.value,
                "provider_identity": price.provider_symbol,
                "listing_id": str(price.listing_id),
                "observed_at": (
                    price.source_updated_at.isoformat() if price.source_updated_at else None
                ),
                "retrieved_at": price.retrieved_at.isoformat(),
                "source_mode": "COMPLETED_DAILY",
                "warning": "COMPLETED_SESSION_INDICATIVE_ONLY",
                "execution_usable": "false",
            },
        ),
    )


class CycleProductValuations:
    """Share one immutable valuation between this cycle's stop and target checks."""

    def __init__(self, source: ProductValuationReader) -> None:
        self._source = source
        self._values: dict[UUID, ProductPositionValuation | None] = {}

    async def for_trade(self, trade_id: UUID) -> ProductPositionValuation | None:
        if trade_id not in self._values:
            self._values[trade_id] = await self._source.for_trade(trade_id)
        return self._values[trade_id]
