"""Chart projection of existing warrant evidence, without fetching or storing prices.

Samples are bounded by capture order, but chart windows and coordinates use only
the original quote clock. Retention contributes at most its actual last success;
it cannot reconstruct a series. Historical source identities are never replaced
by today's preferred provider, listing currency or mapping version.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.service.quote_history import POLICY, QUOTE, sample_status, utc
from app.features.market_data.service.types import MarketDataResult
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

MAX_HISTORY_SAMPLES = 10_000
RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])
PriceKind = Literal["BID", "ASK", "LAST_TRADE", "PREVIOUS_CLOSE"]
Storage = Literal["SAMPLE", "RETAINED"]


@dataclass(frozen=True)
class HistoricalPricePoint:
    id: str
    observed_at: datetime
    price: Decimal
    captured_at: datetime | None
    retrieved_at: datetime
    status: str
    storage: Storage
    quote_time_basis: str | None


@dataclass(frozen=True)
class HistoricalPriceSeries:
    id: str
    provider: str
    identity_key: str
    warrant_listing_id: UUID
    isin: str
    currency: str
    price_kind: PriceKind
    source_mode: str | None
    points: tuple[HistoricalPricePoint, ...]
    provider_exchange_code: str | None = None
    venue_mic: str | None = None


@dataclass(frozen=True)
class WarrantPriceHistory:
    warrant_id: UUID
    isin: str | None
    window_start: datetime | None
    window_end: datetime
    collection_started_at: datetime | None
    samples_considered: int
    samples_available: int
    truncated: bool
    excluded: dict[str, int]
    series: tuple[HistoricalPriceSeries, ...]
    sample_limit: int = MAX_HISTORY_SAMPLES
    sampling_policy: str = POLICY


@dataclass(frozen=True)
class _Observation:
    id: str
    provider: str
    identity_key: str
    listing_id: UUID
    isin: str
    quote: WarrantQuoteSnapshot | None
    retrieved_at: datetime | None
    captured_at: datetime | None
    status: str
    storage: Storage


def _receipt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone(UTC) if parsed.utcoffset() is not None else None


def _sample(row: WarrantQuoteSampleModel) -> _Observation:
    if not isinstance(row.payload, dict):
        raise ValueError("Sample payload is not an object")
    return _Observation(
        str(row.id),
        row.provider,
        row.identity_key,
        row.warrant_listing_id,
        row.isin,
        QUOTE.validate_python(row.payload["quote"]) if row.payload.get("quote") else None,
        _receipt(row.payload.get("retrieved_at")),
        utc(row.captured_at),
        "REQUEST_FAILED" if row.reason else row.status,
        "SAMPLE",
    )


def _retained(row: WarrantQuoteObservationModel) -> _Observation:
    result = RESULT.validate_python(row.payload)
    quote = result.data
    if result.provider.value != row.provider or result.quality_status != QualityStatus.VALID:
        raise ValueError("Retained quote is not validated")
    return _Observation(
        f"retained:{row.warrant_listing_id}:{row.provider}",
        row.provider,
        row.identity_key,
        row.warrant_listing_id,
        quote.provider_symbol if quote else "",
        quote,
        result.retrieved_at,
        None,  # The retention table has no historical capture clock.
        sample_status(quote, None, result.retrieved_at),
        "RETAINED",
    )


def _excluded_reason(
    item: _Observation, isin: str | None, start: datetime | None, now: datetime
) -> str | None:
    q = item.quote
    if item.status in {"REQUEST_FAILED", "NO_QUOTE", "TIME_INCONSISTENT"}:
        return item.status
    if q is None:
        return "NO_QUOTE"
    if (
        not isin
        or item.isin != isin
        or q.provider_symbol != isin
        or (q.isin is not None and q.isin != isin)
        or q.warrant_listing_id != item.listing_id
        or not item.identity_key
    ):
        return "IDENTITY_MISMATCH"
    if q.observed_at is None:
        return "TIMESTAMP_UNKNOWN"
    if (
        item.retrieved_at is None
        or item.retrieved_at.utcoffset() is None
        or q.observed_at > item.retrieved_at
        or item.retrieved_at > now
        or (item.captured_at is not None and item.retrieved_at > item.captured_at)
    ):
        return "TIME_INCONSISTENT"
    if start is not None and q.observed_at < start:
        return "OUTSIDE_WINDOW"
    if q.bid is None and q.ask is None and q.reference_price is None:
        return "NO_PRICE"
    return None


def _series(
    observations: list[_Observation],
    *,
    isin: str | None,
    start: datetime | None,
    now: datetime,
    excluded: Counter[str],
) -> tuple[HistoricalPriceSeries, ...]:
    # Preserve original venue evidence, including an unknown MIC. Today's listing
    # or provider mapping must not rewrite the source of a historical price.
    groups: dict[
        tuple[str, str, UUID, str, str, PriceKind, str | None, str, str | None],
        list[HistoricalPricePoint],
    ] = {}
    seen: set[tuple[str, datetime, Decimal]] = set()
    for item in observations:
        reason = _excluded_reason(item, isin, start, now)
        if reason:
            excluded[reason] += 1
            continue
        q = item.quote
        assert q is not None and q.observed_at is not None and item.retrieved_at is not None
        prices: list[tuple[PriceKind, Decimal | None]] = [("BID", q.bid), ("ASK", q.ask)]
        if q.reference_price_type is not None:
            prices.append((q.reference_price_type, q.reference_price))
        added = False
        for kind, price in prices:
            if price is None:
                continue
            key = (
                item.provider,
                item.identity_key,
                item.listing_id,
                item.isin,
                q.currency,
                kind,
                q.source_mode,
                q.provider_exchange_code,
                q.venue_mic,
            )
            series_id = hashlib.sha256("|".join(map(str, key)).encode()).hexdigest()
            evidence = (series_id, q.observed_at, price)
            if evidence in seen:
                continue
            seen.add(evidence)
            added = True
            groups.setdefault(key, []).append(
                HistoricalPricePoint(
                    f"{item.id}:{kind}",
                    q.observed_at,
                    price,
                    item.captured_at,
                    item.retrieved_at,
                    item.status,
                    item.storage,
                    q.quote_time_basis,
                )
            )
        if not added:
            excluded["DUPLICATE_OBSERVATION"] += 1
    return tuple(
        HistoricalPriceSeries(
            id=hashlib.sha256("|".join(map(str, key)).encode()).hexdigest(),
            provider=key[0],
            identity_key=key[1],
            warrant_listing_id=key[2],
            isin=key[3],
            currency=key[4],
            price_kind=key[5],
            source_mode=key[6],
            points=tuple(sorted(points, key=lambda p: (p.observed_at, p.id))),
            provider_exchange_code=key[7],
            venue_mic=key[8],
        )
        for key, points in sorted(groups.items(), key=lambda pair: tuple(map(str, pair[0])))
    )


async def read_price_series(
    session: AsyncSession,
    workspace_id: UUID,
    warrant_id: UUID,
    *,
    now: datetime,
    days: int | None = None,
) -> WarrantPriceHistory | None:
    if now.utcoffset() is None or (days is not None and not 1 <= days <= 366):
        raise ValueError("Invalid history window")
    now = now.astimezone(UTC)
    start = now - timedelta(days=days) if days is not None else None
    warrant = await session.scalar(
        select(WarrantModel).where(
            WarrantModel.id == warrant_id, WarrantModel.workspace_id == workspace_id
        )
    )
    if warrant is None:
        return None
    m = WarrantQuoteSampleModel
    owner = (m.workspace_id == workspace_id, m.warrant_id == warrant_id, m.captured_at <= now)
    count = await session.scalar(select(func.count(m.id)).where(*owner)) or 0
    first = await session.scalar(select(func.min(m.captured_at)).where(*owner))
    rows = (
        await session.scalars(
            select(m)
            .where(*owner)
            .order_by(m.captured_at.desc(), m.id.desc())
            .limit(MAX_HISTORY_SAMPLES)
        )
    ).all()
    retained = (
        await session.scalars(
            select(WarrantQuoteObservationModel)
            .join(
                WarrantListingModel,
                WarrantListingModel.id == WarrantQuoteObservationModel.warrant_listing_id,
            )
            .where(
                WarrantQuoteObservationModel.workspace_id == workspace_id,
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.warrant_id == warrant_id,
            )
            .order_by(
                WarrantQuoteObservationModel.warrant_listing_id,
                WarrantQuoteObservationModel.provider,
            )
        )
    ).all()
    excluded: Counter[str] = Counter()
    observations = []
    # Prefer the first sampled receipt over repeated cache reads/retention copies.
    for sample in reversed(rows):
        try:
            observations.append(_sample(sample))
        except (ValueError, TypeError, KeyError):
            excluded["INVALID_OBSERVATION"] += 1
    for last in retained:
        try:
            observations.append(_retained(last))
        except (ValueError, TypeError, KeyError):
            excluded["INVALID_OBSERVATION"] += 1
    series = _series(observations, isin=warrant.isin, start=start, now=now, excluded=excluded)
    return WarrantPriceHistory(
        warrant_id,
        warrant.isin,
        start,
        now,
        utc(first) if first else None,
        len(rows),
        count,
        count > len(rows),
        dict(sorted(excluded.items())),
        series,
    )
