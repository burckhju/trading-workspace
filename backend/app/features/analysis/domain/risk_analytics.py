"""Qualified short-horizon analytics; independent of the immutable FT006 V1 gate."""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import pairwise

from app.features.analysis.domain.indicators import realized_volatility, simple_average
from app.features.analysis.domain.models import SnapshotRow
from app.features.analysis.domain.position_analytics import _true_range
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.models import DailyPrice

RISK_ANALYTICS_VERSION = "POSITION_RISK_ANALYTICS_V1"


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    status: str
    reason: str
    session: date | None = None
    window_start: date | None = None
    observations: int = 0
    adjusted_close: Decimal | None = None
    sma20: Decimal | None = None
    distance_sma20: Decimal | None = None
    sma20_slope: Decimal | None = None
    realized_volatility20: Decimal | None = None
    previous_volatility20: Decimal | None = None
    atr14_relative: Decimal | None = None
    atr_reason: str = "INSUFFICIENT_HISTORY"
    price_field: str = "ADJUSTED_CLOSE"
    annualization: int = 252
    policy_version: str = RISK_ANALYTICS_VERSION


def weekday_gap(previous: date, current: date) -> bool:
    """Detect unproven gaps, not infer exchange holidays from a weekday calendar."""
    day = previous + timedelta(days=1)
    while day < current:
        if day.weekday() < 5:
            return True
        day += timedelta(days=1)
    return False


def rounded(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)


def risk_metrics(
    prices: tuple[DailyPrice, ...], *, as_of: datetime, max_age_days: int = 4
) -> RiskMetrics:
    """Use 21 completed adjusted closes; never bridge missing sessions silently.

    EOD dates have no verified session-close instant. Exclude today's rows.
    No exchange calendar exists in the current contract: a missing weekday
    therefore remains an explicit limitation, including a possible holiday.
    """
    if as_of.utcoffset() is None:
        raise ValueError("evaluation time must be timezone-aware")
    if any(a.trading_date >= b.trading_date for a, b in pairwise(prices)):
        return RiskMetrics("NOT_EVALUABLE", "DATES_NOT_STRICTLY_INCREASING")
    completed = tuple(price for price in prices if price.trading_date < as_of.date())
    if len(completed) < 21:
        return RiskMetrics(
            "NOT_EVALUABLE", "NEED_21_COMPLETED_ADJUSTED_CLOSES", observations=len(completed)
        )
    window = completed[-21:]
    latest = window[-1]
    context = RiskMetrics(
        "NOT_EVALUABLE",
        "",
        session=latest.trading_date,
        window_start=window[0].trading_date,
        observations=len(window),
    )
    if (as_of.date() - latest.trading_date).days > max_age_days:
        return replace(context, reason="EOD_STALE")
    reason = _window_error(window, as_of)
    if reason:
        return replace(context, reason=reason)
    closes = [p.adjusted_close for p in window if p.adjusted_close is not None]
    average = simple_average(closes, 20)
    previous_average = simple_average(closes[:-1], 20)
    volatility = realized_volatility(closes, 20, Decimal(252))
    previous_volatility = None
    if len(completed) >= 41:
        earlier = completed[-41:-20]
        if _window_error(earlier, as_of) is None and _same_identity(earlier[-1], latest):
            previous_volatility = rounded(
                realized_volatility(
                    [p.adjusted_close for p in earlier if p.adjusted_close is not None],
                    20,
                    Decimal(252),
                )
            )
    atr, atr_reason = _relative_atr(window[-15:])
    return replace(
        context,
        status="AVAILABLE",
        reason="QUALIFIED_COMPLETED_OBSERVATIONS",
        adjusted_close=latest.adjusted_close,
        sma20=rounded(average),
        distance_sma20=rounded(closes[-1] / average - 1),
        sma20_slope=rounded(average / previous_average - 1),
        realized_volatility20=rounded(volatility),
        previous_volatility20=previous_volatility,
        atr14_relative=atr,
        atr_reason=atr_reason,
    )


def _same_identity(first: DailyPrice, second: DailyPrice) -> bool:
    return (
        first.listing_id,
        first.market_data_instrument_id,
        first.currency,
        first.provider,
        first.provider_symbol,
    ) == (
        second.listing_id,
        second.market_data_instrument_id,
        second.currency,
        second.provider,
        second.provider_symbol,
    )


def _window_error(window: tuple[DailyPrice, ...], as_of: datetime) -> str | None:
    if any(not _same_identity(p, window[0]) for p in window):
        return "SERIES_IDENTITY_OR_CURRENCY_CHANGED"
    if any(p.quality_status is not QualityStatus.VALID or p.warnings for p in window):
        return "EOD_QUALITY_LIMITED"
    if any(p.adjusted_close is None for p in window):
        return "ADJUSTED_CLOSE_MISSING"
    if any(
        p.retrieved_at > as_of or (p.source_updated_at is not None and p.source_updated_at > as_of)
        for p in window
    ):
        return "DATA_NOT_KNOWN_AT_EVALUATION"
    if any(p.trading_date.weekday() >= 5 for p in window):
        return "SESSION_CALENDAR_UNVERIFIED"
    if any(weekday_gap(a.trading_date, b.trading_date) for a, b in pairwise(window)):
        return "MISSING_SESSION_OR_UNVERIFIED_HOLIDAY"
    return None


def _relative_atr(window: tuple[DailyPrice, ...]) -> tuple[Decimal | None, str]:
    # Adjusted closes must never be compared with raw highs/lows. Raw ATR is
    # meaningful on its own axis only while its adjustment scale stays stable.
    factors = [p.adjusted_close / p.close for p in window if p.adjusted_close is not None]
    if not factors or max(factors) / min(factors) - 1 > Decimal("0.000001"):
        return None, "CORPORATE_ACTION_OR_ADJUSTMENT_CHANGE"
    rows = [
        SnapshotRow(
            p.trading_date,
            p.open,
            p.high,
            p.low,
            p.close,
            p.adjusted_close,
            p.volume,
            p.currency,
            p.provider.value,
            p.provider_symbol,
            p.quality_status.value,
            p.warnings,
        )
        for p in window
    ]
    atr = (
        sum((_true_range(row, previous.close) for previous, row in pairwise(rows)), Decimal(0)) / 14
    )
    return rounded(atr / window[-1].close), "RAW_OHLC_ATR14_DIVIDED_BY_RAW_CLOSE"
