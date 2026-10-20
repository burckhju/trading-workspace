"""Descriptive same-instant returns, not leverage, fair value or execution P&L."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SynchronizedPricePair:
    underlying_id: UUID
    underlying_listing_id: UUID
    warrant_id: UUID
    warrant_listing_id: UUID
    terms_id: UUID
    provider: str
    underlying_currency: str
    warrant_currency: str
    underlying_observed_at: datetime
    warrant_observed_at: datetime
    received_at: datetime
    underlying_price: Decimal
    bid: Decimal
    ask: Decimal | None
    ratio: Decimal
    direction: str
    quality: str = "VALID"
    retained: bool = False
    adjustment_basis: str = "UNADJUSTED_SAME_TERMS"


@dataclass(frozen=True, slots=True)
class ProductComparison:
    status: str
    reasons: tuple[str, ...]
    price_type: str = "BID_TO_BID"
    underlying_return: Decimal | None = None
    warrant_return: Decimal | None = None
    direction_adjusted_underlying_return: Decimal | None = None
    descriptive_divergence: bool | None = None
    normalized_underlying: tuple[Decimal, ...] = ()
    normalized_warrant: tuple[Decimal, ...] = ()
    times: tuple[datetime, ...] = ()
    policy_version: str = "SYNCHRONOUS_PRODUCT_COMPARISON_V1"
    execution_usable: bool = False


def compare_product(
    points: tuple[SynchronizedPricePair, ...], *, as_of: datetime, price_type: str = "BID_TO_BID"
) -> ProductComparison:
    def blocked(reason: str) -> ProductComparison:
        return ProductComparison("NOT_EVALUABLE", (reason,), price_type)

    if as_of.utcoffset() is None or price_type not in {"BID_TO_BID", "MID_INDICATION"}:
        return blocked("INVALID_COMPARISON_REQUEST")
    if len(points) < 2:
        return blocked("NEED_TWO_DISTINCT_SYNCHRONIZED_OBSERVATIONS")
    first = points[0]

    def identity(p: SynchronizedPricePair) -> tuple[object, ...]:
        return (
            p.underlying_id,
            p.underlying_listing_id,
            p.warrant_id,
            p.warrant_listing_id,
            p.terms_id,
            p.provider,
            p.ratio,
            p.direction,
            p.underlying_currency,
            p.warrant_currency,
            p.adjustment_basis,
        )

    prices: list[Decimal] = []
    previous_time: datetime | None = None
    for point in points:
        if identity(point) != identity(first):
            return blocked("IDENTITY_TERMS_OR_ADJUSTMENT_CHANGED")
        if point.underlying_currency != point.warrant_currency:
            return blocked("FX_OR_QUANTO_CONTEXT_UNVERIFIED")
        if point.adjustment_basis != "UNADJUSTED_SAME_TERMS":
            return blocked("ADJUSTMENT_BASIS_UNVERIFIED")
        if point.direction not in {"CALL", "PUT"}:
            return blocked("PRODUCT_DIRECTION_UNKNOWN")
        times = (point.underlying_observed_at, point.warrant_observed_at, point.received_at)
        if any(t.utcoffset() is None for t in times):
            return blocked("SOURCE_TIME_OR_TIMEZONE_UNKNOWN")
        if point.underlying_observed_at != point.warrant_observed_at:
            return blocked("PRICE_INSTANTS_NOT_SYNCHRONOUS")
        if (
            point.warrant_observed_at > point.received_at
            or point.received_at > as_of
            or (previous_time is not None and point.warrant_observed_at <= previous_time)
        ):
            return blocked("REPEATED_OUT_OF_ORDER_OR_FUTURE_OBSERVATION")
        if point.quality != "VALID" or point.retained:
            return blocked("QUOTE_RETAINED_OR_QUALITY_LIMITED")
        if any(
            not v.is_finite() or v <= 0
            for v in (
                point.underlying_price,
                point.bid,
                point.ratio,
            )
        ):
            return blocked("INVALID_PRICE_OR_RATIO")
        if point.ask is not None and (not point.ask.is_finite() or point.ask < point.bid):
            return blocked("INVALID_TWO_SIDED_QUOTE")
        if price_type == "MID_INDICATION":
            if point.ask is None:
                return blocked("MID_REQUIRES_TWO_SIDED_QUOTE")
            prices.append((point.bid + point.ask) / 2)
        else:
            prices.append(point.bid)
        previous_time = point.warrant_observed_at
    stock_return = points[-1].underlying_price / first.underlying_price - 1
    product_return = prices[-1] / prices[0] - 1
    directed = stock_return * (1 if first.direction == "CALL" else -1)
    return ProductComparison(
        "AVAILABLE",
        ("DESCRIPTIVE_ONLY_NO_MODEL_EXPECTATION",),
        price_type,
        stock_return,
        product_return,
        directed,
        directed > 0 and product_return < 0,
        tuple(p.underlying_price / first.underlying_price * 100 for p in points),
        tuple(p / prices[0] * 100 for p in prices),
        tuple(p.warrant_observed_at for p in points),
    )
