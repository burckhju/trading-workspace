"""Obtain a price for the user's confirmed rule identity, without cross-instrument fallback."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
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


MAX_INDICATION_RECEIPT_AGE_SECONDS = 300


def _issuer_indication_error(value: ProductPositionValuation, now: datetime) -> str | None:
    contract = ISSUER_INDICATIONS.get(value.selected_source or "")
    if (
        contract is None
        or value.quote_provider != value.selected_source
        or value.source_mode != contract[0]
        or value.quote_time_basis != contract[1]
        or value.source_selection_status != "SELECTED"
        or value.source_selection_policy_version != contract[2]
        or value.provider_exchange_code != "ISSUER"
        or value.provider_identity != value.isin
        or not value.quote_time_text
        or value.reference_price_type != "BID"
        or value.bid is None
        or value.reference_price != value.bid
    ):
        return "INVALID_QUOTE_TIMESTAMP"
    if value.quote_retained or value.quote_refresh_error:
        return "ISSUER_INDICATION_REFRESH_FAILED"
    received = value.quote_retrieved_at
    if received is None or received.utcoffset() is None or received > now:
        return "INVALID_INDICATION_RECEIPT_TIMESTAMP"
    if (now - received).total_seconds() > MAX_INDICATION_RECEIPT_AGE_SECONDS:
        return "ISSUER_INDICATION_RECEIPT_TOO_OLD"
    return None


async def rule_price(
    *,
    subject: MonitoringSubject,
    rule: MonitoringRule,
    market_data: LatestCompletedDailyPriceProvider | None,
    products: ProductValuationReader | None,
    now: datetime,
    max_age_days: int,
    checked_at: Callable[[], datetime] | None = None,
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
        # A network fetch may finish after cycle start. Validate against the clock after it.
        assessment_at = checked_at() if checked_at else now
        observed_at = value.quote_observed_at
        indication = observed_at is None
        if observed_at is None:
            error = _issuer_indication_error(value, assessment_at)
            if error:
                status = (
                    "MISSING"
                    if "REFRESH_FAILED" in error
                    else "STALE" if error == "ISSUER_INDICATION_RECEIPT_TOO_OLD" else "ERROR"
                )
                return RulePriceResult(status, error)
        elif observed_at.utcoffset() is None or observed_at > assessment_at:
            return RulePriceResult("ERROR", "INVALID_QUOTE_TIMESTAMP")
        # Never promote Last/Close to Bid, nor indicative monitoring to execution permission.
        warning = value.analysis_warning or (
            "INDICATIVE_REFERENCE_PRICE" if value.reference_price_type != "BID" else None
        )
        if indication:
            warning = ISSUER_INDICATIONS[value.selected_source][3]
        context = {
            "price_type": value.reference_price_type,
            "provider": value.selected_source,
            "provider_identity": value.provider_identity,
            "isin": value.isin,
            "listing_id": str(value.quote_listing_id),
            "venue_mic": value.quote_venue_mic,
            "provider_exchange_code": value.provider_exchange_code,
            "source_mode": value.source_mode,
            "trading_status": value.trading_status,
            "delay_seconds": (
                str(value.quote_delay_seconds) if value.quote_delay_seconds is not None else None
            ),
            "observed_at": value.quote_observed_at.isoformat() if value.quote_observed_at else None,
            "retrieved_at": (
                value.quote_retrieved_at.isoformat() if value.quote_retrieved_at else None
            ),
            "warning": warning,
            "refresh_error": value.quote_refresh_error,
            "execution_usable": "false",
            "quote_time_text": value.quote_time_text,
            "quote_time_basis": value.quote_time_basis,
            "evaluation_mode": "INDICATIVE_ISSUER" if indication else "SOURCE_TIMESTAMP",
            "ordering_time_basis": "RECEIPT_TIMESTAMP" if indication else "SOURCE_TIMESTAMP",
            "source_freshness": "UNKNOWN" if indication else None,
        }
        return RulePriceResult(
            "INDICATIVE" if warning else "AVAILABLE",
            "ISSUER_INDICATION_CHECKED" if indication else "WARRANT_REFERENCE_PRICE_CHECKED",
            PriceObservation(
                value.reference_price,
                value.quote_observed_at,
                binding,
                context,
                received_at=value.quote_retrieved_at,
            ),
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
