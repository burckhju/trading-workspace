"""Finite source/calendar contracts with disposable storage and intercepted HTTP."""

import base64
import hashlib
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_session_evidence_service import (
    SqlSession,
)

from app.features.market_data.domain.review_calendars import (
    NYSE_CALENDAR,
    calendar_days,
)
from app.features.market_data.persistence.review_calendars import ReviewCalendarModel
from app.features.market_data.service import review_calendars as owner
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    SessionEntry,
    count_completed_sessions,
)
from app.features.position_monitoring.service import (
    indicative_entry_sessions as consumer,
)
from app.features.product.persistence.price_scale_evidence import fingerprint

NOW = datetime(2026, 11, 18, 15, tzinfo=UTC)
WORKSPACE = uuid4()
ORIGINAL = b"Synthetic finite calendar source; not a real provider."


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    async def blocked(*_args, **_kwargs):
        raise AssertionError("Unintercepted provider request")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)


@pytest.fixture
def stored(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/synthetic-review-{uuid4()}.db")
    ReviewCalendarModel.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session, SqlSession(session)
    engine.dispose()


def payload():
    return {
        "sources": [
            {
                "sha256": hashlib.sha256(ORIGINAL).hexdigest(),
                "document_base64": base64.b64encode(ORIGINAL).decode(),
            }
        ],
        "days": TypeAdapter(list[dict]).dump_python(
            [asdict(day) for day in calendar_days(NYSE_CALENDAR)], mode="json"
        ),
    }


def save(sql, *, values=None, when=NOW):
    values = payload() if values is None else values
    row = ReviewCalendarModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        venue_mic="XNYS",
        source_version=NYSE_CALENDAR.source_version,
        recorded_at=when,
        payload=values,
        fingerprint=fingerprint(values),
    )
    sql.add(row)
    sql.commit()
    return row


def test_published_special_closure_early_close_and_dst_are_preserved():
    days = {day.session_date: day for day in calendar_days(NYSE_CALENDAR)}
    assert len(days) == 1095
    assert days[date(2025, 1, 9)].status == "CLOSED"
    assert days[date(2026, 11, 26)].status == "CLOSED"
    assert days[date(2026, 11, 27)].intervals[0].closes_at.astimezone(UTC).hour == 18
    assert days[date(2026, 10, 29)].intervals[0].closes_at.astimezone(UTC).hour == 20
    assert days[date(2026, 11, 2)].intervals[0].closes_at.astimezone(UTC).hour == 21


def test_twentieth_close_between_quote_and_receipt_does_not_requalify_old_quote():
    entry = SessionEntry(uuid4(), datetime(2026, 10, 1, 14, tzinfo=UTC), None, None, "EXACT")
    args = dict(entry=entry, binding=NYSE_CALENDAR.binding, days=calendar_days(NYSE_CALENDAR))
    old_bid = count_completed_sessions(**args, event_at=datetime(2026, 10, 29, 19, 59, tzinfo=UTC))
    later_read = count_completed_sessions(
        **args, event_at=datetime(2026, 10, 29, 20, 1, tzinfo=UTC)
    )
    assert old_bid.completed_sessions == 19 and not old_bid.threshold_reached
    assert later_read.completed_sessions == 20 and later_read.threshold_reached
    assert date(2026, 10, 1) not in later_read.completed_session_dates


async def test_source_requires_exact_original_bytes_and_rejects_redirects():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=ORIGINAL)),
        trust_env=False,
    ) as client:
        assert (
            await owner.fetch_calendar_source(
                client,
                "https://example.invalid/calendar",
                hashlib.sha256(ORIGINAL).hexdigest(),
            )
            == base64.b64encode(ORIGINAL).decode()
        )
        with pytest.raises(ValueError, match="REVISION_CHANGED"):
            await owner.fetch_calendar_source(client, "https://example.invalid/calendar", "0" * 64)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                302, headers={"location": "https://example.invalid/other"}
            )
        ),
        trust_env=False,
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await owner.fetch_calendar_source(client, "https://example.invalid/calendar", "0" * 64)


async def test_read_is_known_at_scoped_and_preserves_original_integrity(stored):
    sql, session = stored
    row = save(sql)
    assert (
        await owner.read_calendar(
            session,
            workspace_id=WORKSPACE,
            source_version=row.source_version,
            known_at=NOW - timedelta(seconds=1),
        )
        is None
    )
    assert (
        await owner.read_calendar(
            session,
            workspace_id=uuid4(),
            source_version=row.source_version,
            known_at=NOW,
        )
        is None
    )
    session.commit.reset_mock()
    session.flush.reset_mock()
    result = await owner.read_calendar(
        session, workspace_id=WORKSPACE, source_version=row.source_version, known_at=NOW
    )
    assert result.id == row.id
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
    row.payload = {**row.payload, "injected": True}
    with pytest.raises(ValueError, match="INTEGRITY_FAILURE"):
        await owner.read_calendar(
            session,
            workspace_id=WORKSPACE,
            source_version=row.source_version,
            known_at=NOW,
        )


async def test_document_bytes_checked_even_if_payload_fingerprint_is_recomputed(stored):
    sql, session = stored
    values = payload()
    values["sources"][0]["document_base64"] = base64.b64encode(b"changed").decode()
    row = save(sql, values=values)
    with pytest.raises(ValueError, match="INTEGRITY_FAILURE"):
        await owner.read_calendar(
            session,
            workspace_id=WORKSPACE,
            source_version=row.source_version,
            known_at=NOW,
        )


async def test_indicative_date_only_counts_conservatively_without_changing_strict_contract(
    stored, monkeypatch
):
    sql, session = stored
    save(sql)
    underlying = uuid4()

    async def product(*_args, **_kwargs):
        return (
            SimpleNamespace(id=uuid4()),
            SimpleNamespace(underlying_id=underlying),
            SimpleNamespace(reference_venue_mic="XNYS"),
            (),
        )

    monkeypatch.setattr(
        consumer.ProductReviewEvidenceReader, "reference_market_for_review", product
    )
    entry = SessionEntry(uuid4(), None, date(2026, 10, 1), "Europe/Berlin", "DATE_ONLY")
    strict = count_completed_sessions(
        entry=entry,
        binding=NYSE_CALENDAR.binding,
        days=calendar_days(NYSE_CALENDAR),
        event_at=NOW,
    )
    assert strict.reasons == ("ENTRY_CALENDAR_DAY_AMBIGUOUS",)
    count, material = await consumer.read_review_session_count(
        session,
        workspace_id=WORKSPACE,
        warrant_id=uuid4(),
        underlying_id=underlying,
        entry=entry,
        now=NOW,
        event_at=NOW,
    )
    assert count.anchor_date == date(2026, 10, 1)
    assert count.threshold_reached
    assert material["calendar"]["entry_day_precision"] == "CONSERVATIVE_DATE_BOUND"
    assert material["earliest_possible_entry_day"] == "2026-09-30"
    assert entry.executed_at is None and entry.time_precision == "DATE_ONLY"
    missing_count, _ = await consumer.read_review_session_count(
        session,
        workspace_id=WORKSPACE,
        warrant_id=uuid4(),
        underlying_id=uuid4(),
        entry=entry,
        now=NOW,
        event_at=NOW,
    )
    assert missing_count.status == "NOT_ASSESSABLE"


def test_day_only_calendar_has_no_invented_open_close_or_2027_extension():
    rows = owner.xstu_day_rows()
    assert len(rows) == 365
    assert rows[0] == {"session_date": "2026-01-01", "status": "CLOSED"}
    assert rows[-1] == {"session_date": "2026-12-31", "status": "CLOSED"}
    assert set(rows[1]) == {"session_date", "status"}
