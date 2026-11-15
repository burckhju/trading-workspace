"""Synthetic source packages exercise real session and original-evidence boundaries."""

import base64
import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.session_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_SESSION_DAYS,
    SessionBinding,
    SessionDay,
    SessionEvidenceImportCommand,
    SessionManifest,
    SessionWindow,
)
from app.features.market_data.service.session_evidence import validate_import

ZONE = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)
DOCUMENT = b"SYNTHETIC TEST DOCUMENT - no real market calendar.\nSession source page 4."
HASH = hashlib.sha256(DOCUMENT).hexdigest()
ADAPTER = TypeAdapter(SessionManifest)


def window(day=date(2026, 10, 23), start=9, end=17):
    return SessionWindow(
        datetime.combine(day, datetime.min.time(), ZONE) + timedelta(hours=start),
        datetime.combine(day, datetime.min.time(), ZONE) + timedelta(hours=end),
    )


def manifest(**changes):
    return replace(
        SessionManifest(
            calendar_id="SYNTHETIC-calendar",
            calendar_version="synthetic-v1",
            binding=SessionBinding(
                "UNDERLYING",
                UUID(int=1),
                UUID(int=2),
                UUID(int=3),
                "XETR",
                "Europe/Berlin",
                "Synthetic documented continuous trading",
                date(2026, 1, 1),
                date(2026, 12, 31),
            ),
            coverage_start=date(2026, 10, 23),
            coverage_end=date(2026, 10, 25),
            days=(
                SessionDay(date(2026, 10, 23), "SESSION", (window(),), "Synthetic page 4"),
                SessionDay(date(2026, 10, 24), "CLOSED", (), "Synthetic explicit closure page 5"),
                SessionDay(
                    date(2026, 10, 25), "UNKNOWN", (), "Synthetic source does not cover day"
                ),
            ),
            source_publisher="Synthetic publisher",
            source_reference="Synthetic document page 4",
            source_document_sha256=HASH,
        ),
        **changes,
    )


def package(value=None, *, original=None, **changes):
    raw = (
        original
        if original is not None
        else ADAPTER.dump_json(value or manifest(), indent=2).decode()
    )
    return replace(
        SessionEvidenceImportCommand(
            request_id=UUID(int=4),
            supersedes_revision_id=None,
            manifest_json=raw,
            manifest_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            document_filename="synthetic-calendar.txt",
            document_media_type="text/plain",
            document_base64=base64.b64encode(DOCUMENT).decode(),
            document_sha256=HASH,
            reviewed_at=NOW - timedelta(days=1),
            review_reference="Synthetic manual review page 4",
        ),
        **changes,
    )


def test_original_package_preserves_bytes_formatting_and_unknown_source_clocks():
    raw = "\n  " + ADAPTER.dump_json(manifest(), indent=4).decode() + "\n\n"
    command = package(original=raw)
    parsed, document = validate_import(command, NOW)
    assert document == DOCUMENT
    assert parsed == manifest()
    assert command.manifest_json == raw
    assert parsed.source_published_at is parsed.source_published_on is None
    assert command.retrieved_at is None
    with pytest.raises(FrozenInstanceError):
        parsed.calendar_version = "changed"


def test_closed_unknown_and_missing_days_remain_distinct_without_generated_weekends():
    value = manifest(days=(manifest().days[0], manifest().days[2]))
    parsed, _ = validate_import(package(value), NOW)
    assert [item.status for item in parsed.days] == ["SESSION", "UNKNOWN"]
    assert date(2026, 10, 24) not in [item.session_date for item in parsed.days]


def test_broken_and_shortened_sessions_keep_every_original_interval():
    day = SessionDay(
        date(2026, 10, 23),
        "SESSION",
        (window(end=11), window(start=12, end=14)),
        "Synthetic short trading day with explicit break",
    )
    parsed, _ = validate_import(package(manifest(days=(day,))), NOW)
    assert parsed.days == (day,)
    assert parsed.days[0].intervals[0].closes_at < parsed.days[0].intervals[1].opens_at
    assert parsed.days[0].intervals[-1].closes_at.hour == 14


@pytest.mark.parametrize(("day", "hours"), [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)])
def test_dst_calendar_days_keep_real_instant_duration_without_weekday_generation(day, hours):
    opening = datetime.combine(day, datetime.min.time(), ZONE)
    closing = datetime.combine(day + timedelta(days=1), datetime.min.time(), ZONE)
    interval = SessionWindow(opening, closing)
    value = manifest(
        coverage_start=day,
        coverage_end=day,
        days=(SessionDay(day, "SESSION", (interval,), "Synthetic documented DST session"),),
    )
    parsed, _ = validate_import(package(value), NOW)
    actual = parsed.days[0].intervals[0]
    assert (
        actual.closes_at.astimezone(UTC) - actual.opens_at.astimezone(UTC)
    ).total_seconds() == hours * 3600


def test_utc_instants_are_valid_with_explicit_historical_local_session_day():
    original = window()
    utc = SessionWindow(original.opens_at.astimezone(UTC), original.closes_at.astimezone(UTC))
    value = manifest(
        days=(SessionDay(date(2026, 10, 23), "SESSION", (utc,), "Synthetic UTC clock source"),)
    )
    parsed, _ = validate_import(package(value), NOW)
    assert parsed.days[0].intervals == (utc,)


@pytest.mark.parametrize("mic", ["1234", "XETR", "MUND"])
def test_existing_ascii_mic_shape_is_preserved(mic):
    assert replace(manifest().binding, venue_mic=mic).venue_mic == mic


@pytest.mark.parametrize("mic", ["xetr", "ÄETR", "\uff11\uff12\uff13\uff14", "XET", "XETRR"])
def test_mic_rejects_unscoped_or_noncanonical_symbols(mic):
    with pytest.raises(ValueError, match="MIC"):
        replace(manifest().binding, venue_mic=mic)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 10, 23, 9), datetime(2026, 10, 23, 17)),
        (NOW, NOW),
        (NOW, NOW - timedelta(seconds=1)),
    ],
)
def test_no_unknown_or_nonpositive_interval_is_promoted_to_a_session(start, end):
    with pytest.raises(ValueError):
        SessionWindow(start, end)


@pytest.mark.parametrize(
    ("status", "intervals"),
    [
        ("CLOSED", (window(),)),
        ("UNKNOWN", (window(),)),
        ("SESSION", ()),
        ("OPEN", (window(),)),
        ("SESSION", (window(), window(start=10, end=18))),
    ],
)
def test_day_status_and_break_boundaries_cannot_contradict_each_other(status, intervals):
    with pytest.raises(ValueError):
        SessionDay(date(2026, 10, 23), status, intervals, "Synthetic invalid source")


@pytest.mark.parametrize(
    "change",
    [
        "range",
        "validity",
        "duplicate",
        "order",
        "outside",
        "clock",
        "zone",
        "offset",
        "overnight_overlap",
    ],
)
def test_manifest_rejects_contradictory_temporal_and_identity_bounds(change):
    value = manifest()
    with pytest.raises(ValueError):
        if change == "range":
            replace(value, coverage_end=value.coverage_start + timedelta(days=MAX_SESSION_DAYS))
        elif change == "validity":
            replace(value, binding=replace(value.binding, valid_from=date(2026, 10, 24)))
        elif change == "duplicate":
            replace(value, days=(value.days[0], value.days[0]))
        elif change == "order":
            replace(value, days=tuple(reversed(value.days)))
        elif change == "outside":
            replace(value, coverage_end=date(2026, 10, 24))
        elif change == "clock":
            replace(value, source_published_at=datetime(2026, 10, 1))
        elif change == "zone":
            replace(value.binding, timezone="Unknown/Invented")
        elif change == "offset":
            interval = SessionWindow(
                datetime.fromisoformat("2026-10-23T09:00:00+03:00"),
                datetime.fromisoformat("2026-10-23T17:00:00+03:00"),
            )
            replace(
                value,
                days=(
                    SessionDay(
                        date(2026, 10, 23), "SESSION", (interval,), "Synthetic wrong local offset"
                    ),
                ),
            )
        else:
            first = SessionDay(
                date(2026, 10, 23),
                "SESSION",
                (window(start=20, end=27),),
                "Synthetic overnight source",
            )
            second = SessionDay(
                date(2026, 10, 24),
                "SESSION",
                (window(date(2026, 10, 24), start=2, end=6),),
                "Synthetic overlapping source",
            )
            replace(value, days=(first, second))


def test_publication_precision_is_not_silently_promoted_or_duplicated():
    day = date(2026, 10, 1)
    parsed, _ = validate_import(package(manifest(source_published_on=day)), NOW)
    assert parsed.source_published_on == day
    assert parsed.source_published_at is None
    with pytest.raises(ValueError, match="publication"):
        manifest(source_published_on=day, source_published_at=NOW)


@pytest.mark.parametrize(
    "change",
    [
        "manifest_hash",
        "document_hash",
        "document_binding",
        "empty_document",
        "oversize_document",
        "oversize_manifest",
        "bad_base64",
        "media",
        "filename",
        "blank_review",
        "future_review",
        "naive_review",
        "future_retrieval",
        "future_publication",
        "duplicate_json",
        "unknown_field",
        "non_json_number",
        "json",
    ],
)
def test_import_rejects_missing_original_integrity_or_review_provenance(change):
    command = package()
    if change == "manifest_hash":
        command = replace(command, manifest_sha256="0" * 64)
    elif change == "document_hash":
        command = replace(command, document_sha256="0" * 64)
    elif change == "document_binding":
        command = package(manifest(source_document_sha256="0" * 64))
    elif change == "empty_document":
        command = replace(command, document_base64="")
    elif change == "oversize_document":
        command = replace(
            command, document_base64=base64.b64encode(b"x" * (MAX_DOCUMENT_BYTES + 1)).decode()
        )
    elif change == "oversize_manifest":
        command = package(original=" " * (MAX_MANIFEST_BYTES + 1))
    elif change == "bad_base64":
        command = replace(command, document_base64="%%%!")
    elif change == "media":
        command = replace(command, document_media_type="application/x-executable")
    elif change == "filename":
        command = replace(command, document_filename="../original.txt")
    elif change == "blank_review":
        command = replace(command, review_reference="   ")
    elif change == "future_review":
        command = replace(command, reviewed_at=NOW + timedelta(seconds=1))
    elif change == "naive_review":
        command = replace(command, reviewed_at=NOW.replace(tzinfo=None))
    elif change == "future_retrieval":
        command = replace(command, retrieved_at=NOW + timedelta(seconds=1))
    elif change == "future_publication":
        command = package(manifest(source_published_at=NOW + timedelta(seconds=1)))
    elif change == "duplicate_json":
        command = package(
            original=command.manifest_json.replace(
                '"calendar_id":', '"calendar_id": "duplicate", "calendar_id":', 1
            )
        )
    elif change == "unknown_field":
        raw = json.loads(command.manifest_json)
        raw["verified"] = True
        command = package(original=json.dumps(raw))
    elif change == "non_json_number":
        command = package(original='{"calendar_id": NaN}')
    else:
        command = package(original="not JSON")
    with pytest.raises(ApplicationError) as caught:
        validate_import(command, NOW)
    assert caught.value.status_code == 422
    assert caught.value.code == "SESSION_EVIDENCE_INVALID"


def test_later_document_capture_does_not_invent_a_review_clock_or_short_capture_deadline():
    command = package(reviewed_at=NOW - timedelta(days=200), retrieved_at=NOW - timedelta(days=1))
    parsed, original = validate_import(command, NOW)
    assert parsed.source_published_at is None
    assert original == DOCUMENT
    assert command.retrieved_at > command.reviewed_at


def test_documented_withdrawal_remains_explicit_original_evidence():
    value = manifest(evidence_status="WITHDRAWN", days=())
    parsed, original = validate_import(package(value), NOW)
    assert parsed.evidence_status == "WITHDRAWN"
    assert parsed.days == ()
    assert original == DOCUMENT
