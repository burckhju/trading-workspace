"""Additive published-calendar acquisition and passive reads for indicative scope."""

import base64
import hashlib
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.review_calendars import (
    NYSE_CALENDAR,
    VERIFICATION,
    ReviewDay,
    ReviewDayCalendarRead,
    calendar_days,
)
from app.features.market_data.persistence.review_calendars import ReviewCalendarModel
from app.features.product.persistence.models import WarrantListingModel
from app.features.product.persistence.price_scale_evidence import fingerprint

JSON_VALUE = TypeAdapter(dict[str, Any])
MAX_BYTES = 2_000_000


async def fetch_calendar_source(client: httpx.AsyncClient, url: str, digest: str) -> str:
    async with client.stream("GET", url, follow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("REVIEW_CALENDAR_SOURCE_UNAVAILABLE")
        document = bytearray()
        async for chunk in response.aiter_bytes():
            document.extend(chunk)
            if len(document) > MAX_BYTES:
                raise ValueError("REVIEW_CALENDAR_SOURCE_TOO_LARGE")
    if hashlib.sha256(document).hexdigest() != digest:
        raise ValueError("REVIEW_CALENDAR_SOURCE_REVISION_CHANGED")
    return base64.b64encode(document).decode("ascii")


async def acquire_nyse_calendar(
    session: AsyncSession,
    client: httpx.AsyncClient,
    *,
    workspace_id: UUID,
    now: datetime,
) -> None:
    definition = NYSE_CALENDAR
    exists = await session.scalar(
        select(ReviewCalendarModel.id).where(
            ReviewCalendarModel.workspace_id == workspace_id,
            ReviewCalendarModel.source_version == definition.source_version,
        )
    )
    if exists is not None:
        return
    sources = []
    for url, digest in definition.sources:
        sources.append(
            {
                "url": url,
                "sha256": digest,
                "document_base64": await fetch_calendar_source(client, url, digest),
            }
        )
    payload = JSON_VALUE.dump_python(
        {
            "definition": asdict(definition),
            "days": [asdict(day) for day in calendar_days(definition)],
            "sources": sources,
            "verification": VERIFICATION,
        },
        mode="json",
    )
    await session.execute(
        insert(ReviewCalendarModel)
        .values(
            id=uuid4(),
            workspace_id=workspace_id,
            venue_mic=definition.binding.venue_mic,
            source_version=definition.source_version,
            recorded_at=now,
            payload=payload,
            fingerprint=fingerprint(payload),
        )
        .on_conflict_do_nothing(index_elements=["workspace_id", "source_version"])
    )


async def read_calendar(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    source_version: str,
    known_at: datetime,
) -> ReviewCalendarModel | None:
    with session.no_autoflush:
        row = await session.scalar(
            select(ReviewCalendarModel).where(
                ReviewCalendarModel.workspace_id == workspace_id,
                ReviewCalendarModel.source_version == source_version,
                ReviewCalendarModel.recorded_at <= known_at,
            )
        )
        if row is not None:
            if fingerprint(row.payload) != row.fingerprint:
                raise ValueError("REVIEW_CALENDAR_STORED_INTEGRITY_FAILURE")
            for source in row.payload["sources"]:
                raw = base64.b64decode(source["document_base64"], validate=True)
                if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                    raise ValueError("REVIEW_CALENDAR_STORED_INTEGRITY_FAILURE")
        return row


XSTU_DAY_VERSION = "xstu-dates-2026-reviewed-20261118-v1"
XSTU_DAY_URL = "https://www.boerse-stuttgart.de/media/wabiiobs/2026-07-21_bk_handelskalender_2026_aktualisierung_20260721.pdf"
XSTU_DAY_SHA256 = "0426c32af27ae7c040f4ec15a50c5c483051ca97ee3215976982a5c3583ee717"


async def acquire_xstu_day_calendar(
    session: AsyncSession,
    client: httpx.AsyncClient,
    *,
    workspace_id: UUID,
    now: datetime,
) -> None:
    exists = await session.scalar(
        select(ReviewCalendarModel.id).where(
            ReviewCalendarModel.workspace_id == workspace_id,
            ReviewCalendarModel.source_version == XSTU_DAY_VERSION,
        )
    )
    if exists is not None:
        return
    source = await fetch_calendar_source(client, XSTU_DAY_URL, XSTU_DAY_SHA256)
    payload: dict[str, Any] = {
        "days": xstu_day_rows(),
        "precision": "DAY_ONLY",
        "verification": VERIFICATION,
        "sources": [{"url": XSTU_DAY_URL, "sha256": XSTU_DAY_SHA256, "document_base64": source}],
    }
    await session.execute(
        insert(ReviewCalendarModel)
        .values(
            id=uuid4(),
            workspace_id=workspace_id,
            venue_mic="XSTU",
            source_version=XSTU_DAY_VERSION,
            recorded_at=now,
            payload=payload,
            fingerprint=fingerprint(payload),
        )
        .on_conflict_do_nothing(index_elements=["workspace_id", "source_version"])
    )


async def read_review_deadline_calendar(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    listing_id: UUID,
    venue_mic: str,
    known_at: datetime,
) -> ReviewDayCalendarRead:
    row = (
        await read_calendar(
            session,
            workspace_id=workspace_id,
            source_version=XSTU_DAY_VERSION,
            known_at=known_at,
        )
        if venue_mic == "XSTU"
        else None
    )
    actual = await session.scalar(
        select(WarrantListingModel.id)
        .join(
            TradingVenueModel,
            TradingVenueModel.id == WarrantListingModel.trading_venue_id,
        )
        .where(
            WarrantListingModel.id == listing_id,
            WarrantListingModel.workspace_id == workspace_id,
            WarrantListingModel.warrant_id == warrant_id,
            TradingVenueModel.mic == venue_mic,
            TradingVenueModel.is_active.is_(True),
        )
    )
    reasons = (
        ("REVIEW_DAY_CALENDAR_BINDING_CHANGED",)
        if actual is None
        else ("REVIEW_DAY_CALENDAR_MISSING",) if row is None else ()
    )
    start, end = (date(2026, 1, 1), date(2026, 12, 31)) if row else (None, None)
    days = (
        tuple(
            ReviewDay(date.fromisoformat(d["session_date"]), d["status"])
            for d in row.payload["days"]
        )
        if row
        else ()
    )
    return ReviewDayCalendarRead(
        workspace_id,
        warrant_id,
        listing_id,
        venue_mic,
        "Europe/Berlin",
        known_at,
        row.recorded_at if row else None,
        row.id if row else None,
        fingerprint(
            {
                "calendar": row.fingerprint if row else None,
                "listing_id": listing_id,
                "reasons": reasons,
            }
        ),
        VERIFICATION,
        "UNSUITABLE" if actual is None else "MISSING" if row is None else "AVAILABLE",
        reasons,
        start,
        end,
        days,
        XSTU_DAY_URL if row else None,
        start,
        end,
    )


def xstu_day_rows() -> list[dict[str, str]]:
    closed = {
        date(2026, month, day)
        for month, day in ((1, 1), (4, 3), (4, 6), (5, 1), (12, 24), (12, 25), (12, 31))
    }
    start = date(2026, 1, 1)
    return [
        {
            "session_date": (day := start + timedelta(days=n)).isoformat(),
            "status": "CLOSED" if day.weekday() >= 5 or day in closed else "SESSION",
        }
        for n in range(365)
    ]
