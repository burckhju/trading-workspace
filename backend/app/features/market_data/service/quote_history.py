"""Bounded UTC sampling of existing reads; no fetch, backfill, IV or alert side effects."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import WarrantQuoteSampleModel
from app.features.market_data.persistence.quote_identity import QuoteIdentity
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.persistence.models import WarrantModel

POLICY = "FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1"
STATUSES = (
    "TWO_SIDED_WITHIN_AGE_LIMIT",
    "ONE_SIDED",
    "REFERENCE_ONLY",
    "TIMESTAMP_UNKNOWN",
    "TIME_INCONSISTENT",
    "STALE",
    "AGE_POLICY_UNKNOWN",
    "REQUEST_FAILED",
    "NO_QUOTE",
)
QUOTE = TypeAdapter(WarrantQuoteSnapshot)


def utc(value: datetime) -> datetime:
    # SQLite reads an explicitly UTC-stored database clock without tzinfo.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def sample_status(quote: WarrantQuoteSnapshot | None, reason: str | None, now: datetime) -> str:
    if reason is not None:
        return "NO_QUOTE" if reason == "WARRANT_NO_QUOTE_RETURNED" else "REQUEST_FAILED"
    if quote is None:
        return "NO_QUOTE"
    if quote.observed_at is None:
        return "TIMESTAMP_UNKNOWN"
    if quote.observed_at > now:
        return "TIME_INCONSISTENT"
    if quote.reference_price is not None:
        return "REFERENCE_ONLY"
    if quote.max_quote_age_seconds is None:
        return "AGE_POLICY_UNKNOWN"
    if (now - quote.observed_at).total_seconds() > quote.max_quote_age_seconds:
        return "STALE"
    if quote.bid is None or quote.ask is None:
        return "ONE_SIDED"
    return "TWO_SIDED_WITHIN_AGE_LIMIT"


async def capture_quote_sample(
    session: AsyncSession,
    *,
    request: WarrantQuoteRequest,
    warrant_id: UUID,
    provider: str,
    identity: QuoteIdentity,
    result: MarketDataResult[WarrantQuoteSnapshot | None] | None,
    reason: str | None,
    captured_at: datetime,
) -> None:
    """Caller holds listing lock, rechecked identity, commits atomically with retention.

    The first completed read wins regardless of outcome. Later successes in that
    slot still update last-success storage, but cannot replace the sampled failure.
    """
    if captured_at.utcoffset() is None:
        raise ValueError("Capture clock must be timezone aware")
    now = captured_at.astimezone(UTC)
    slot = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
    found = await session.scalar(
        select(WarrantQuoteSampleModel.id).where(
            WarrantQuoteSampleModel.workspace_id == request.workspace_id,
            WarrantQuoteSampleModel.warrant_listing_id == request.warrant_listing_id,
            WarrantQuoteSampleModel.provider == provider,
            WarrantQuoteSampleModel.identity_key == identity.key,
            WarrantQuoteSampleModel.slot_at == slot,
        )
    )
    if found is not None:
        return
    quote = result.data if result is not None and reason is None else None
    data = QUOTE.dump_python(quote, mode="json") if quote else None
    fingerprint = None
    if data is not None:
        normalized = {
            k: v for k, v in data.items() if k not in {"assessed_at", "retained", "refresh_error"}
        }
        fingerprint = hashlib.sha256(
            json.dumps([identity.key, normalized], sort_keys=True).encode()
        ).hexdigest()
    session.add(
        WarrantQuoteSampleModel(
            id=uuid4(),
            workspace_id=request.workspace_id,
            warrant_id=warrant_id,
            warrant_listing_id=request.warrant_listing_id,
            provider=provider,
            identity_key=identity.key,
            isin=identity.isin,
            slot_at=slot,
            day_utc=slot.date(),
            captured_at=now,
            status=(
                "TIME_INCONSISTENT"
                if reason is None and result is not None and result.retrieved_at > now
                else sample_status(quote, reason, now)
            ),
            reason=(
                reason
                if reason is None or re.fullmatch(r"[A-Za-z0-9_]{1,140}", reason)
                else "UNCLASSIFIED_PROVIDER_ERROR"
            ),
            quote_fingerprint=fingerprint,
            payload={
                "quote": data,
                "retrieved_at": result.retrieved_at.isoformat() if result else None,
                "cache_status": result.cache_status.value if result else None,
                "policy_version": POLICY,
            },
        )
    )


@dataclass(frozen=True)
class QuoteHistoryItem:
    id: UUID
    provider: str
    identity_key: str
    isin: str
    captured_at: datetime
    slot_at: datetime
    status: str
    reason: str | None
    quote_fingerprint: str | None
    quote: WarrantQuoteSnapshot | None
    retrieved_at: datetime | None
    cache_status: str | None


@dataclass(frozen=True)
class QuoteHistorySegment:
    provider: str
    identity_key: str
    isin: str
    sampled_slots: int
    distinct_quote_evidence: int
    observed_utc_days: int
    first_capture_at: datetime
    last_capture_at: datetime
    statuses: dict[str, int]


@dataclass(frozen=True)
class QuoteHistoryReport:
    warrant_id: UUID
    window_start: datetime
    window_end: datetime
    collection_started_at: datetime | None
    segments: tuple[QuoteHistorySegment, ...]
    items: tuple[QuoteHistoryItem, ...]
    sampling_policy: str = POLICY
    item_limit: int = 50
    time_coverage_percent: None = None
    iv_history_available: bool = False
    underlying_synchronization_available: bool = False
    execution_usable: bool = False


class QuoteHistoryReader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def report(
        self,
        workspace_id: UUID,
        warrant_id: UUID,
        *,
        now: datetime,
        days: int = 7,
    ) -> QuoteHistoryReport | None:
        if now.utcoffset() is None or not 1 <= days <= 31:
            raise ValueError("Invalid history window")
        exists = await self.session.scalar(
            select(WarrantModel.id).where(
                WarrantModel.id == warrant_id, WarrantModel.workspace_id == workspace_id
            )
        )
        if exists is None:
            return None
        start = now - timedelta(days=days)
        m = WarrantQuoteSampleModel
        owner = (m.workspace_id == workspace_id, m.warrant_id == warrant_id)
        window = (*owner, m.captured_at >= start, m.captured_at <= now)
        first = await self.session.scalar(
            select(func.min(m.captured_at)).where(*owner, m.captured_at <= now)
        )
        grouped = (
            await self.session.execute(
                select(
                    m.provider,
                    m.identity_key,
                    m.isin,
                    func.count(m.id),
                    func.count(distinct(m.quote_fingerprint)),
                    func.count(distinct(m.day_utc)),
                    func.min(m.captured_at),
                    func.max(m.captured_at),
                    *(func.sum(case((m.status == s, 1), else_=0)) for s in STATUSES),
                )
                .where(*window)
                .group_by(m.provider, m.identity_key, m.isin)
                .order_by(m.provider, m.identity_key)
            )
        ).all()
        segments = tuple(
            QuoteHistorySegment(
                r[0],
                r[1],
                r[2],
                r[3],
                r[4],
                r[5],
                utc(r[6]),
                utc(r[7]),
                dict(zip(STATUSES, r[8:], strict=True)),
            )
            for r in grouped
        )
        rows = (
            await self.session.scalars(
                select(m).where(*window).order_by(m.captured_at.desc(), m.id.desc()).limit(50)
            )
        ).all()
        items = tuple(
            QuoteHistoryItem(
                r.id,
                r.provider,
                r.identity_key,
                r.isin,
                utc(r.captured_at),
                utc(r.slot_at),
                r.status,
                r.reason,
                r.quote_fingerprint,
                QUOTE.validate_python(r.payload["quote"]) if r.payload["quote"] else None,
                (
                    datetime.fromisoformat(r.payload["retrieved_at"])
                    if r.payload["retrieved_at"]
                    else None
                ),
                r.payload["cache_status"],
            )
            for r in rows
        )
        return QuoteHistoryReport(
            warrant_id, start, now, utc(first) if first else None, segments, items
        )
