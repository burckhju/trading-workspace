"""Explicit V2 reference-market assumption, retaining the existing session counter."""

from dataclasses import asdict
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.review_calendars import NYSE_CALENDAR, VERIFICATION
from app.features.market_data.domain.session_evidence import SessionDay
from app.features.market_data.service.review_calendars import read_calendar
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    CompletedSessionCount,
    SessionAnchor,
    SessionEntry,
    count_completed_sessions,
    count_sessions_from_anchor,
    session_anchor,
    unavailable_session_count,
)
from app.features.product.service.review_evidence import ProductReviewEvidenceReader


async def read_review_session_count(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    underlying_id: UUID,
    entry: SessionEntry | None,
    now: datetime,
    event_at: datetime,
) -> tuple[CompletedSessionCount, dict[str, Any]]:
    product, binding, facts, problems = await ProductReviewEvidenceReader(
        session
    ).reference_market_for_review(
        workspace_id=workspace_id,
        warrant_id=warrant_id,
        known_at=now,
    )
    reasons = list(problems)
    if binding is None or binding.underlying_id != underlying_id:
        reasons.append("REVIEW_REFERENCE_MARKET_BINDING_MISSING")
    calendar = None
    if facts is None or facts.reference_venue_mic != "XNYS":
        reasons.append("REVIEW_REFERENCE_CALENDAR_NOT_COVERED")
    else:
        calendar = await read_calendar(
            session,
            workspace_id=workspace_id,
            source_version=NYSE_CALENDAR.source_version,
            known_at=now,
        )
        if calendar is None:
            reasons.append("REVIEW_REFERENCE_CALENDAR_MISSING")
    material: dict[str, Any] = {
        "calendar_quality": "CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED",
        "verification": VERIFICATION,
        "product_revision_id": str(product.id) if product else None,
        "calendar_revision_id": str(calendar.id) if calendar else None,
        "calendar_fingerprint": calendar.fingerprint if calendar else None,
        "historical_listing_binding_verified": False,
        "event_at": event_at.isoformat(),
    }
    if reasons or calendar is None:
        count = unavailable_session_count(
            event_at=event_at, anchor_date=None, reasons=tuple(dict.fromkeys(reasons))
        )
    else:
        days = TypeAdapter(tuple[SessionDay, ...]).validate_python(calendar.payload["days"])
        count = count_completed_sessions(
            entry=entry, binding=NYSE_CALENDAR.binding, days=days, event_at=event_at
        )
        if (
            entry is not None
            and entry.time_precision == "DATE_ONLY"
            and count.reasons == ("ENTRY_CALENDAR_DAY_AMBIGUOUS",)
            and entry.executed_on is not None
            and entry.execution_timezone is not None
        ):
            # V2 explicitly uses a lower bound, never an invented original timestamp.
            original_zone = ZoneInfo(entry.execution_timezone)
            reference_zone = ZoneInfo(NYSE_CALENDAR.binding.timezone)
            start = datetime.combine(entry.executed_on, time.min, original_zone).astimezone(UTC)
            end = datetime.combine(
                entry.executed_on + timedelta(days=1), time.min, original_zone
            ).astimezone(UTC)
            earliest = start.astimezone(reference_zone).date()
            latest = (end - timedelta(microseconds=1)).astimezone(reference_zone).date()
            count = count_sessions_from_anchor(
                anchor=SessionAnchor(latest, ()),
                binding=NYSE_CALENDAR.binding,
                days=days,
                event_at=event_at,
            )
            material.update(
                entry_day_precision="CONSERVATIVE_DATE_BOUND",
                earliest_possible_entry_day=earliest.isoformat(),
                latest_possible_entry_day=latest.isoformat(),
            )
        else:
            material["entry_day_precision"] = (
                "EXACT_CALENDAR_DAY"
                if not session_anchor(entry, NYSE_CALENDAR.binding, event_at=event_at).reasons
                else "UNRESOLVED"
            )
    material["count"] = asdict(count)
    material["calendar"] = {
        key: value for key, value in material.items() if key not in {"count", "event_at"}
    }
    material["period"] = {
        "source_version": NYSE_CALENDAR.source_version if calendar else None,
        "fingerprint": calendar.fingerprint if calendar else None,
    }
    return count, material
