"""Observed official website REST contract: last trades, never executable bid/ask.

The website's three-character XSC code is retained separately from the internal
Frankfurt listing MIC. Neither response arrival nor trading hours establish an
exchange quote timestamp, feed delay, or current trading status.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.providers.frankfurt_quotes.schema import (
    FRANKFURT_MIC,
    FrankfurtObservation,
    FrankfurtRecord,
    Price,
    QuoteStatus,
    _utc,
)

PUBLIC_URL = "https://api.live.deutsche-boerse.com/v1/data/price_information/single"
PUBLIC_EXCHANGE_CODE = "XSC"
PUBLIC_SOURCE = "deutsche-boerse-public"
PUBLIC_MODE = "OFFICIAL_WEBSITE_LAST_TRADE"


class PublicCurrency(BaseModel):
    originalValue: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class FrankfurtPublicPrice(BaseModel):
    # Other website fields (day high/low, underlying-independent turnover, etc.)
    # are deliberately not turned into quotes or executable sizes.
    model_config = ConfigDict(frozen=True)

    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    mic: Literal["XSC"]
    currency: PublicCurrency
    lastPrice: Price | None = None
    timestampLastPrice: datetime | None = None
    closingPricePrevTradingDay: Price | None = None

    @field_validator("timestampLastPrice", mode="before")
    @classmethod
    def timestamp(cls, value: Any) -> datetime | None:
        return None if value is None else _utc(value)


def assess_public_price(
    price: FrankfurtPublicPrice,
    *,
    isin: str,
    currency: str,
    now: datetime,
    retrieved_at: datetime,
    max_age_seconds: int,
) -> FrankfurtObservation:
    now, retrieved_at = _utc(now), _utc(retrieved_at)
    use_last = price.lastPrice is not None
    # No date accompanies closingPricePrevTradingDay in this wire contract.
    observed_at = price.timestampLastPrice if use_last else None
    age = (now - observed_at).total_seconds() if observed_at is not None else None
    status, reason = QuoteStatus.INSUFFICIENT, "FRANKFURT_POST_TRADE_ONLY"
    record = None
    if price.isin != isin:
        status, reason = QuoteStatus.ERROR, "FRANKFURT_ISIN_MISMATCH"
    elif price.currency.originalValue != currency:
        status, reason = QuoteStatus.ERROR, "FRANKFURT_CURRENCY_MISMATCH"
    elif retrieved_at > now or (observed_at is not None and observed_at > retrieved_at):
        status, reason = QuoteStatus.ERROR, "FRANKFURT_TIMESTAMP_INCONSISTENT"
    else:
        record = FrankfurtRecord(
            isin=price.isin,
            mic=FRANKFURT_MIC,
            currency=price.currency.originalValue,
            kind="LAST_TRADE" if use_last else "PREVIOUS_CLOSE",
            last_price=price.lastPrice if use_last else None,
            last_at=observed_at,
            close_price=price.closingPricePrevTradingDay if not use_last else None,
        )
        if not use_last and price.closingPricePrevTradingDay is None:
            status, reason = QuoteStatus.MISSING, "FRANKFURT_LAST_TRADE_MISSING"
        elif observed_at is None:
            reason = "FRANKFURT_REFERENCE_TIMESTAMP_UNKNOWN"
        elif age is not None and age > max_age_seconds:
            status, reason = QuoteStatus.STALE, "FRANKFURT_LAST_TRADE_STALE"
    return FrankfurtObservation(
        status=status,
        reason=reason,
        source=PUBLIC_SOURCE,
        isin=isin,
        assessed_at=now,
        retrieved_at=retrieved_at,
        snapshot_generated_at=None,
        declared_delay_seconds=None,
        max_quote_age_seconds=max_age_seconds,
        observed_at=observed_at,
        age_seconds=age,
        record=record,
        provider_exchange_code=PUBLIC_EXCHANGE_CODE,
        source_mode=PUBLIC_MODE if use_last else "OFFICIAL_WEBSITE_PREVIOUS_CLOSE",
    )
