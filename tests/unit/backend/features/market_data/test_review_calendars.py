"""Finite source/calendar contracts with disposable storage and intercepted HTTP."""

import base64
import hashlib
import io
import json
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_session_evidence_service import (
    SqlSession,
)

from app.core.config import Settings
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
from app.tools import import_review_calendar_original as local_import

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


@pytest.fixture
def local_original(monkeypatch):
    # No third-party document is redistributed in the repository or test data.
    raw = b"%PDF-1.4\nSynthetic reviewed local calendar; not an exchange document.\n"
    monkeypatch.setattr(owner, "XSTU_DAY_SHA256", hashlib.sha256(raw).hexdigest())
    return raw


def test_xstu_original_import_retains_the_existing_reviewed_source_pin():
    assert owner.XSTU_DAY_VERSION == "xstu-dates-2026-reviewed-20261118-v1"
    assert owner.XSTU_DAY_SHA256 == (
        "0426c32af27ae7c040f4ec15a50c5c483051ca97ee3215976982a5c3583ee717"
    )
    assert owner.XSTU_DAY_URL == (
        "https://www.boerse-stuttgart.de/media/wabiiobs/"
        "2026-07-21_bk_handelskalender_2026_aktualisierung_20260721.pdf"
    )


async def test_local_preview_has_no_insert_flush_commit_or_network(stored, local_original):
    sql, session = stored
    result = await owner.import_xstu_day_calendar_original(
        session, workspace_id=WORKSPACE, document=local_original, now=NOW
    )
    assert result["mode"] == "PREVIEW" and result["outcome"] == "READY_TO_IMPORT"
    assert result["provider_requests"] is False
    assert list(sql.scalars(select(ReviewCalendarModel))) == []
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
    assert all(statement.is_select for statement in session.statements)


async def test_local_original_import_is_private_day_only_and_reused_without_network(
    stored, local_original
):
    sql, session = stored
    result = await owner.import_xstu_day_calendar_original(
        session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
    )
    sql.commit()
    assert result["outcome"] == "IMPORTED"
    row = sql.scalar(select(ReviewCalendarModel))
    row_id, original_payload, original_fingerprint = row.id, row.payload, row.fingerprint
    acquisition = row.payload["acquisition"]
    assert acquisition == {
        "method": "USER_SUPPLIED_ORIGINAL",
        "verification": "USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION",
        "time_basis": "FILE_RECEIVED_AT",
        "received_at": NOW.isoformat(),
    }
    assert result["stored_acquisition"] == acquisition
    assert row.payload["precision"] == "DAY_ONLY"
    assert row.payload["verification"] == owner.VERIFICATION
    assert len(row.payload["days"]) == 365
    assert set(row.payload["days"][0]) == {"session_date", "status"}
    assert row.payload["days"][-1]["session_date"] == "2026-12-31"
    assert base64.b64decode(row.payload["sources"][0]["document_base64"]) == local_original
    later = await owner.import_xstu_day_calendar_original(
        session,
        workspace_id=WORKSPACE,
        document=local_original,
        now=NOW + timedelta(days=1),
        apply=True,
    )
    assert later["outcome"] == "ALREADY_AVAILABLE"
    assert later["stored_acquisition"]["received_at"] == NOW.isoformat()
    async with httpx.AsyncClient(trust_env=False) as client:
        await owner.acquire_xstu_day_calendar(
            session, client, workspace_id=WORKSPACE, now=NOW + timedelta(days=1)
        )
    retained = sql.scalar(select(ReviewCalendarModel))
    assert retained.id == row_id
    assert retained.payload == original_payload and retained.fingerprint == original_fingerprint
    assert len(list(sql.scalars(select(ReviewCalendarModel)))) == 1


@pytest.mark.parametrize("invalid", [b"", b"changed original", b"x" * (owner.MAX_BYTES + 1)])
async def test_local_import_rejects_missing_changed_and_oversized_originals_before_writes(
    stored, local_original, invalid
):
    sql, session = stored
    with pytest.raises(ValueError, match="REVIEW_CALENDAR_SOURCE_"):
        await owner.import_xstu_day_calendar_original(
            session, workspace_id=WORKSPACE, document=invalid, now=NOW, apply=True
        )
    assert session.statements == []
    assert list(sql.scalars(select(ReviewCalendarModel))) == []


@pytest.mark.parametrize("corrupt", ["bytes", "days", "source", "fingerprint"])
async def test_import_and_readiness_cannot_replace_a_corrupt_existing_original(
    stored, local_original, corrupt
):
    sql, session = stored
    await owner.import_xstu_day_calendar_original(
        session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
    )
    row = sql.scalar(select(ReviewCalendarModel))
    values = json.loads(json.dumps(row.payload))
    if corrupt == "bytes":
        values["sources"][0]["document_base64"] = base64.b64encode(b"tampered").decode()
    elif corrupt == "days":
        values["days"][0]["status"] = "SESSION"
    elif corrupt == "source":
        values["sources"][0]["url"] = "https://example.invalid/another-source"
    row.payload = values
    row.fingerprint = "0" * 64 if corrupt == "fingerprint" else fingerprint(values)
    sql.commit()
    before = (row.id, row.payload, row.fingerprint)
    with pytest.raises(ValueError, match="STORED_INTEGRITY_FAILURE"):
        await owner.import_xstu_day_calendar_original(
            session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
        )
    async with httpx.AsyncClient(trust_env=False) as client:
        with pytest.raises(ValueError, match="STORED_INTEGRITY_FAILURE"):
            await owner.acquire_xstu_day_calendar(session, client, workspace_id=WORKSPACE, now=NOW)
    assert (row.id, row.payload, row.fingerprint) == before


async def test_local_import_never_relabels_existing_network_origin_or_other_workspace(
    stored, local_original
):
    sql, session = stored
    await owner.import_xstu_day_calendar_original(
        session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
    )
    row = sql.scalar(select(ReviewCalendarModel))
    row.payload = {key: value for key, value in row.payload.items() if key != "acquisition"}
    row.fingerprint = fingerprint(row.payload)
    sql.commit()
    original = (row.id, row.payload, row.fingerprint)
    result = await owner.import_xstu_day_calendar_original(
        session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
    )
    assert result["stored_acquisition"] is None
    assert (row.id, row.payload, row.fingerprint) == original
    other = await owner.import_xstu_day_calendar_original(
        session, workspace_id=uuid4(), document=local_original, now=NOW
    )
    assert other["outcome"] == "READY_TO_IMPORT"
    assert len(list(sql.scalars(select(ReviewCalendarModel)))) == 1


async def test_local_import_does_not_overwrite_a_future_revision(stored, local_original):
    sql, session = stored
    await owner.import_xstu_day_calendar_original(
        session,
        workspace_id=WORKSPACE,
        document=local_original,
        now=NOW + timedelta(minutes=1),
        apply=True,
    )
    sql.commit()
    with pytest.raises(ValueError, match="KNOWLEDGE_TIME_INVALID"):
        await owner.import_xstu_day_calendar_original(
            session, workspace_id=WORKSPACE, document=local_original, now=NOW, apply=True
        )
    assert len(list(sql.scalars(select(ReviewCalendarModel)))) == 1


@pytest.mark.parametrize("apply", [False, True])
async def test_local_cli_uses_configured_workspace_and_explicit_apply_only(
    stored, local_original, tmp_path, monkeypatch, apply
):
    sql, session = stored
    path = tmp_path / "synthetic-local-calendar.pdf"
    path.write_bytes(local_original)

    @asynccontextmanager
    async def session_context():
        yield session

    database = SimpleNamespace(session_context=session_context, dispose=AsyncMock())
    settings = Settings.model_construct(database_echo=True)
    settings.market_data.refresh.workspace_id = WORKSPACE
    monkeypatch.setattr(local_import, "get_settings", lambda: settings)

    def database_manager(actual_settings):
        assert actual_settings is not settings and actual_settings.database_echo is False
        return database

    monkeypatch.setattr(local_import, "DatabaseManager", database_manager)
    monkeypatch.setattr(local_import, "datetime", SimpleNamespace(now=lambda _zone: NOW))
    result = await local_import._run(SimpleNamespace(file=path, apply=apply))
    assert result["outcome"] == ("IMPORTED" if apply else "READY_TO_IMPORT")
    assert session.commit.await_count == int(apply)
    session.rollback.assert_awaited_once()
    database.dispose.assert_awaited_once()
    assert settings.database_echo is True
    statements = [str(statement) for statement in session.statements]
    assert statements[0] == (
        "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"
        if apply
        else "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    )
    rows = list(sql.scalars(select(ReviewCalendarModel)))
    assert len(rows) == int(apply)
    if apply:
        assert rows[0].workspace_id == WORKSPACE


def test_local_cli_reads_bounded_stdin_and_rejects_symlinks_and_special_files(
    local_original, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        local_import.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(local_original))
    )
    assert local_import.read_original(Path("-")) == local_original
    original = tmp_path / "calendar.pdf"
    original.write_bytes(local_original)
    link = tmp_path / "link.pdf"
    link.symlink_to(original)
    with pytest.raises(OSError):
        local_import.read_original(link)
    fifo = tmp_path / "not-a-regular-file"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="SOURCE_FILE_INVALID"):
        local_import.read_original(fifo)


def test_local_cli_defaults_to_preview_and_does_not_print_exception_payloads(monkeypatch, capsys):
    seen = []

    async def run(args):
        seen.append(args)
        raise RuntimeError("postgresql://private-user:private-password@private-host")

    monkeypatch.setattr(local_import, "_run", run)
    assert local_import.main(["--file", "local.pdf"]) == 1
    assert seen[0].apply is False
    assert json.loads(capsys.readouterr().out) == {
        "outcome": "FAILED",
        "problem": "REVIEW_CALENDAR_IMPORT_FAILED",
    }
