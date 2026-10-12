"""Audit current IV availability from owner evidence; never invent provider fields.

V1 deliberately cannot produce a current IV: the persisted provider contracts lack
IV/Greeks, verified exercise/Quanto facts and a synchronized underlying quote.
This capability limit must be changed together with a qualified ingestion path.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.features.market.service.risk_reference import RiskListingReference
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.product.service.risk_reference import RiskProductReference


@dataclass(frozen=True, slots=True)
class IvReadiness:
    reasons: tuple[str, ...]
    quote_side: str | None = None
    quote_age_seconds: int | None = None
    status: str = "NOT_EVALUABLE"
    risk_level: str | None = None
    current_iv_decimal: Decimal | None = None
    iv_origin: str | None = None
    change_pp: Decimal | None = None
    percentile: Decimal | None = None
    rank: Decimal | None = None
    vega_per_warrant_per_pp: Decimal | None = None
    position_iv_effect: Decimal | None = None
    next_event: str | None = None
    selected_scenario_loss: Decimal | None = None
    history_status: str = "NO_QUALIFIED_IV_HISTORY"
    event_status: str = "NO_VERIFIED_EVENT_SOURCE"
    policy_version: str = "IV_READINESS_V1"
    model_version: str | None = None
    execution_usable: bool = False


def assess_iv_readiness(
    product: RiskProductReference | None,
    listing: RiskListingReference | None,
    evidence: SavedQuoteEvidence,
    *,
    as_of: datetime,
) -> IvReadiness:
    reasons = [
        "PROVIDER_IV_AND_GREEKS_NOT_INGESTED",
        "SYNCHRONIZED_UNDERLYING_QUOTE_MISSING",
        "RATE_AND_DIVIDEND_ASSUMPTIONS_MISSING",
        "SESSION_CALENDAR_UNVERIFIED_NO_AGE_EXTENSION",
    ]
    if product is None or product.terms_id is None:
        reasons.append("PRODUCT_TERMS_OR_PRIMARY_LISTING_MISSING")
    if product is None or product.product_type != "VANILLA_WARRANT":
        reasons.append("VANILLA_PRODUCT_TYPE_UNVERIFIED")
    if product is None or product.exercise_style is None:
        reasons.append("EXERCISE_STYLE_UNKNOWN")
    elif product.exercise_style != "EUROPEAN":
        reasons.append("UNSUPPORTED_PRODUCT_OR_EXERCISE")
    if product is None or product.quanto is None:
        reasons.append("QUANTO_STATUS_UNKNOWN")
    elif product.quanto:
        reasons.append("FX_OR_QUANTO_UNSUPPORTED")
    if product is None or product.ratio_convention != "UNDERLYING_UNITS_PER_WARRANT":
        reasons.append("RATIO_CONVENTION_UNVERIFIED")
    if product is None or product.direction not in {"CALL", "PUT"}:
        reasons.append("PRODUCT_DIRECTION_UNKNOWN")
    if product is None or any(
        value is None or not value.is_finite() or value <= 0
        for value in (product.strike, product.ratio)
    ):
        reasons.append("INVALID_PRICE_OR_RATIO")
    if product is None or product.maturity is None:
        reasons.append("MATURITY_MISSING")
    elif product.maturity <= as_of.date():
        reasons.append("MATURITY_REACHED_OR_TODAY")
    else:
        reasons.append("EXACT_EXPIRY_TIME_UNVERIFIED")
    quote = evidence.quote
    age = None
    side: str | None = None
    if quote is None:
        reasons.extend(("WARRANT_QUOTE_MISSING", evidence.reason))
    else:
        if product is None or not product.isin or quote.isin != product.isin:
            reasons.append("POSITION_QUOTE_IDENTITY_MISMATCH")
        if not evidence.provider or not evidence.identity_key:
            reasons.append("QUOTE_PROVENANCE_INCOMPLETE")
        if quote.reference_price is not None:
            side = quote.reference_price_type
            reasons.append("REFERENCE_PRICE_NOT_CURRENT_IV_BASIS")
        elif quote.bid is None or quote.ask is None:
            side = "BID_ONLY" if quote.bid is not None else "ASK_ONLY" if quote.ask else None
            reasons.append("MID_REQUIRES_TWO_SIDED_QUOTE")
        else:
            # WarrantQuoteSnapshot validates positive uncrossed bid/ask at ingestion.
            side = "MID_INDICATION"
        if quote.observed_at is None or quote.observed_at.utcoffset() is None:
            reasons.append("SOURCE_TIME_OR_TIMEZONE_UNKNOWN")
        elif quote.observed_at > as_of:
            reasons.append("QUOTE_TIME_IN_FUTURE")
        else:
            age = int((as_of - quote.observed_at).total_seconds())
            if quote.max_quote_age_seconds is None:
                reasons.append("QUOTE_AGE_POLICY_UNKNOWN")
            elif age > quote.max_quote_age_seconds:
                reasons.append("QUOTE_STALE")
        if evidence.retrieved_at is None:
            reasons.append("QUOTE_RECEIPT_UNKNOWN")
        elif evidence.retrieved_at.utcoffset() is None or evidence.retrieved_at > as_of:
            reasons.append("QUOTE_RECEIPT_INVALID")
        elif quote.observed_at and quote.observed_at > evidence.retrieved_at:
            reasons.append("SAVED_QUOTE_IDENTITY_OR_TIME_INVALID")
        if quote.retained or quote.refresh_error:
            reasons.append("QUOTE_RETAINED_OR_REFRESH_FAILED")
        reasons.append(evidence.refresh_status)
    currencies = (
        product.strike_currency if product else None,
        listing.currency if listing else None,
        quote.currency if quote else None,
    )
    if any(c is None for c in currencies):
        reasons.append("VALUATION_CURRENCY_UNKNOWN")
    elif len(set(currencies)) != 1:
        reasons.append("FX_OR_QUANTO_UNSUPPORTED")
    return IvReadiness(tuple(dict.fromkeys(reasons)), side, age)
