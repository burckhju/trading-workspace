"""Compose the existing calendar owner at BID and read time in one snapshot."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.risk_evidence import SavedQuoteRouteBinding
from app.features.market_data.domain.session_evidence import (
    InstrumentKind,
    SessionEvidenceCurrent,
    SessionEvidenceRead,
)
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.position_monitoring.domain.hebeltrader_original_bid import (
    DocumentedSessionMatch,
    OriginalBidAssessment,
    documented_session_at,
)
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    SessionEntry,
    count_completed_sessions,
    session_anchor,
    unavailable_session_count,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    ProductSessionPrerequisites,
    UnderlyingSessionsAtBid,
)
from app.features.position_monitoring.service.hebeltrader_session_contracts import SessionPeriodView


def inconsistent_read() -> ApplicationError:
    return ApplicationError(
        code="HEBELTRADER_ORIGINAL_BID_READ_INCONSISTENT",
        message="Geldkurs-, Positions- und Kalenderbelege konnten nicht konsistent gelesen werden.",
        status_code=503,
    )


def empty_period() -> SessionPeriodView:
    return SessionPeriodView(None, None, "NOT_REQUESTED", None, (), ())


async def current_calendar(
    reader: SessionEvidenceReader,
    *,
    workspace_id: UUID,
    kind: InstrumentKind,
    instrument_id: UUID,
    now: datetime,
    listing_id: UUID | None = None,
) -> SessionEvidenceCurrent:
    current = await reader.current(
        workspace_id=workspace_id,
        instrument_kind=kind,
        instrument_id=instrument_id,
        known_at=now,
        expected_listing_id=listing_id,
    )
    if (
        current.workspace_id != workspace_id
        or current.instrument_kind != kind
        or current.instrument_id != instrument_id
        or current.known_at != now
        or (
            current.binding is not None
            and (
                current.binding.instrument_kind != kind
                or current.binding.instrument_id != instrument_id
                or (
                    current.status == "AVAILABLE"
                    and listing_id is not None
                    and current.binding.listing_id != listing_id
                )
            )
        )
    ):
        raise inconsistent_read()
    return current


async def read_period(
    reader: SessionEvidenceReader,
    current: SessionEvidenceCurrent,
    *,
    start: date,
    end: date,
) -> tuple[SessionPeriodView, SessionEvidenceRead]:
    assert current.binding is not None
    evidence = await reader.read(
        workspace_id=current.workspace_id,
        instrument_kind=current.instrument_kind,
        instrument_id=current.instrument_id,
        start_date=start,
        end_date=end,
        known_at=current.known_at,
        expected_listing_id=current.binding.listing_id,
    )
    if (
        any(
            getattr(evidence, name) != getattr(current, name)
            for name in (
                "workspace_id",
                "instrument_kind",
                "instrument_id",
                "known_at",
                "revision_id",
                "revision_number",
                "supersedes_revision_id",
                "binding",
                "source",
                "calendar_id",
                "calendar_version",
                "recorded_at",
                "evidence_status",
                "coverage_start",
                "coverage_end",
            )
        )
        or evidence.start_date != start
        or evidence.end_date != end
    ):
        raise inconsistent_read()
    return (
        SessionPeriodView(
            start, end, evidence.status, evidence.fingerprint, evidence.missing_dates, evidence.days
        ),
        evidence,
    )


async def product_sessions(
    reader: SessionEvidenceReader,
    *,
    route: SavedQuoteRouteBinding | None,
    bid: OriginalBidAssessment,
    now: datetime,
) -> ProductSessionPrerequisites:
    current = None
    period = empty_period()
    reasons = bid.reasons or ("PRODUCT_CALENDAR_ROUTE_MISSING",)
    if route is not None:
        current = await current_calendar(
            reader,
            workspace_id=route.workspace_id,
            kind="WARRANT",
            instrument_id=route.warrant_id,
            now=now,
            listing_id=route.warrant_listing_id,
        )
        reasons = tuple(dict.fromkeys((*bid.reasons, *current.reasons)))
        if current.status == "AVAILABLE" and current.binding is not None:
            if (
                current.binding.trading_venue_id != route.trading_venue_id
                or current.binding.venue_mic != route.venue_mic
            ):
                raise inconsistent_read()
            if bid.status == "AVAILABLE" and bid.original_bid_at is not None:
                zone = ZoneInfo(current.binding.timezone)
                dates = (bid.original_bid_at.astimezone(zone).date(), now.astimezone(zone).date())
                # At most 900 seconds separate the events. The preceding local
                # day is required for overnight intervals, never assumed closed.
                period, evidence = await read_period(
                    reader, current, start=min(dates) - timedelta(days=1), end=max(dates)
                )
                reasons = evidence.reasons
                if evidence.status == "COMPLETE" and not reasons:
                    at_bid = documented_session_at(days=evidence.days, event_at=bid.original_bid_at)
                    at_read = documented_session_at(days=evidence.days, event_at=now)
                    relation = "NOT_ASSESSABLE"
                    if at_bid.interval is not None and at_read.interval is not None:
                        relation = (
                            "SAME_INTERVAL"
                            if (
                                at_bid.interval.opens_at.astimezone(UTC),
                                at_bid.interval.closes_at.astimezone(UTC),
                            )
                            == (
                                at_read.interval.opens_at.astimezone(UTC),
                                at_read.interval.closes_at.astimezone(UTC),
                            )
                            else "DIFFERENT_INTERVALS"
                        )
                    return ProductSessionPrerequisites(current, period, at_bid, at_read, relation)
    reasons = reasons or ("PRODUCT_CALENDAR_NOT_ASSESSABLE",)
    return ProductSessionPrerequisites(
        current,
        period,
        DocumentedSessionMatch("NOT_ASSESSABLE", bid.original_bid_at, None, None, reasons),
        DocumentedSessionMatch("NOT_ASSESSABLE", now, None, None, reasons),
        "NOT_ASSESSABLE",
    )


async def underlying_sessions(
    reader: SessionEvidenceReader,
    *,
    workspace_id: UUID,
    underlying_id: UUID,
    entry: SessionEntry | None,
    bid: OriginalBidAssessment,
    now: datetime,
) -> UnderlyingSessionsAtBid:
    current = await current_calendar(
        reader, workspace_id=workspace_id, kind="UNDERLYING", instrument_id=underlying_id, now=now
    )
    period = empty_period()
    if bid.status != "AVAILABLE" or bid.original_bid_at is None:
        return UnderlyingSessionsAtBid(current, period, None)
    event = bid.original_bid_at
    anchor = session_anchor(entry, current.binding, event_at=event)
    reasons = tuple(dict.fromkeys((*current.reasons, *anchor.reasons)))
    if current.status != "AVAILABLE" or current.binding is None or reasons:
        count = unavailable_session_count(
            event_at=event, anchor_date=anchor.day, reasons=reasons or ("SESSION_BINDING_MISSING",)
        )
    else:
        assert anchor.day is not None
        end = event.astimezone(ZoneInfo(current.binding.timezone)).date()
        if end > anchor.day:
            period, evidence = await read_period(
                reader, current, start=anchor.day + timedelta(days=1), end=end
            )
            if evidence.status != "COMPLETE" or evidence.reasons:
                return UnderlyingSessionsAtBid(
                    current,
                    period,
                    unavailable_session_count(
                        event_at=event,
                        anchor_date=anchor.day,
                        reasons=evidence.reasons or ("SESSION_DAYS_MISSING",),
                    ),
                )
        count = count_completed_sessions(
            entry=entry, binding=current.binding, days=period.days, event_at=event
        )
    return UnderlyingSessionsAtBid(current, period, count)
