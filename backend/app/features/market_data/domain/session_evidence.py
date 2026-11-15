"""Explicit document-backed sessions, never a generated exchange calendar."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import ClassVar, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_SESSION_DAYS = 3660
MAX_MANIFEST_BYTES = 2_000_000
MAX_DOCUMENT_BYTES = 2_000_000
type InstrumentKind = Literal["UNDERLYING", "WARRANT"]
type SessionReadStatus = Literal[
    "COMPLETE", "INCOMPLETE", "MISSING", "UNSUITABLE", "LIMIT_EXCEEDED"
]


def aware(value: datetime) -> bool:
    return value.utcoffset() is not None


def reference(value: str, *, maximum: int = 1000) -> None:
    if not isinstance(value, str) or not 3 <= len(value.strip()) <= maximum or "\x00" in value:
        raise ValueError("A concrete bounded evidence reference is required")


@dataclass(frozen=True, slots=True)
class SessionWindow:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    opens_at: datetime
    closes_at: datetime

    def __post_init__(self) -> None:
        if not aware(self.opens_at) or not aware(self.closes_at):
            raise ValueError("Session clocks require explicit UTC offsets")
        if self.closes_at.astimezone(UTC) <= self.opens_at.astimezone(UTC):
            raise ValueError("Session close must be later than its open")


@dataclass(frozen=True, slots=True)
class SessionDay:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    session_date: date
    status: Literal["SESSION", "CLOSED", "UNKNOWN"]
    intervals: tuple[SessionWindow, ...]
    source_reference: str

    def __post_init__(self) -> None:
        reference(self.source_reference)
        if self.status not in {"SESSION", "CLOSED", "UNKNOWN"}:
            raise ValueError("Unknown session day status")
        if (self.status == "SESSION") != bool(self.intervals) or len(self.intervals) > 8:
            raise ValueError("Only a session has one to eight documented trading intervals")
        for previous, current in zip(self.intervals, self.intervals[1:], strict=False):
            if current.opens_at.astimezone(UTC) < previous.closes_at.astimezone(UTC):
                raise ValueError("Session intervals must be ordered and cannot overlap")


@dataclass(frozen=True, slots=True)
class SessionBinding:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    instrument_kind: InstrumentKind
    instrument_id: UUID
    listing_id: UUID
    trading_venue_id: UUID
    venue_mic: str
    timezone: str
    market_segment: str
    valid_from: date
    valid_through: date

    def __post_init__(self) -> None:
        if self.instrument_kind not in {"UNDERLYING", "WARRANT"}:
            raise ValueError("Unknown instrument kind")
        if len(self.venue_mic) != 4 or any(
            char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in self.venue_mic
        ):
            raise ValueError("An explicit four-character MIC is required")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("An explicit IANA timezone is required") from error
        reference(self.market_segment, maximum=200)
        if self.valid_from > self.valid_through or self.valid_through == date.max:
            raise ValueError("Invalid historical binding validity interval")


@dataclass(frozen=True, slots=True)
class SessionManifest:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    calendar_id: str
    calendar_version: str
    binding: SessionBinding
    coverage_start: date
    coverage_end: date
    days: tuple[SessionDay, ...]
    source_publisher: str
    source_reference: str
    source_document_sha256: str
    source_published_at: datetime | None = None
    source_published_on: date | None = None
    evidence_status: Literal["ACTIVE", "WITHDRAWN"] = "ACTIVE"
    schema_version: Literal["session-evidence-manifest-v1"] = "session-evidence-manifest-v1"

    def __post_init__(self) -> None:
        for value in (self.calendar_id, self.calendar_version, self.source_publisher):
            reference(value, maximum=200)
        reference(self.source_reference)
        if self.schema_version != "session-evidence-manifest-v1":
            raise ValueError("Unknown session manifest schema")
        if self.evidence_status not in {"ACTIVE", "WITHDRAWN"}:
            raise ValueError("Unknown calendar evidence status")
        if (
            self.coverage_start > self.coverage_end
            or (self.coverage_end - self.coverage_start).days >= MAX_SESSION_DAYS
            or len(self.days) > MAX_SESSION_DAYS
        ):
            raise ValueError("Session manifest exceeds the bounded coverage range")
        if (
            not self.binding.valid_from
            <= self.coverage_start
            <= self.coverage_end
            <= (self.binding.valid_through)
        ):
            raise ValueError("Coverage must remain inside the declared historical binding")
        if self.source_published_at is not None and (
            not aware(self.source_published_at) or self.source_published_on is not None
        ):
            raise ValueError("Preserve either the known publication clock or its date precision")
        if len(self.source_document_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.source_document_sha256
        ):
            raise ValueError("A SHA256 of the original source document is required")
        dates = [day.session_date for day in self.days]
        if len(set(dates)) != len(dates) or dates != sorted(dates):
            raise ValueError("Session dates must be distinct and ordered")
        zone = ZoneInfo(self.binding.timezone)
        previous_end: datetime | None = None
        for day in self.days:
            if not self.coverage_start <= day.session_date <= self.coverage_end:
                raise ValueError("Session date lies outside the declared coverage")
            for window in day.intervals:
                opening = window.opens_at.astimezone(zone)
                closing = window.closes_at.astimezone(zone)
                if (
                    opening.date() != day.session_date
                    or closing.date() > day.session_date + timedelta(days=1)
                    or window.opens_at.utcoffset() not in {timedelta(0), opening.utcoffset()}
                    or window.closes_at.utcoffset() not in {timedelta(0), closing.utcoffset()}
                ):
                    raise ValueError("Original session clocks must match their local date and zone")
                start, end = window.opens_at.astimezone(UTC), window.closes_at.astimezone(UTC)
                if previous_end is not None and start < previous_end:
                    raise ValueError("Documented sessions cannot overlap across dates")
                previous_end = end


@dataclass(frozen=True, slots=True)
class SessionEvidenceImportCommand:
    request_id: UUID
    supersedes_revision_id: UUID | None
    manifest_json: str
    manifest_sha256: str
    document_filename: str
    document_media_type: str
    document_base64: str
    document_sha256: str
    reviewed_at: datetime
    review_reference: str
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SessionSourceProvenance:
    manifest_sha256: str
    document_sha256: str
    document_filename: str
    document_media_type: str
    publisher: str
    reference: str
    published_at: datetime | None
    published_on: date | None
    retrieved_at: datetime | None
    reviewed_at: datetime
    review_reference: str
    recorded_by: UUID


@dataclass(frozen=True, slots=True)
class SessionEvidenceRevision:
    id: UUID
    workspace_id: UUID
    instrument_kind: InstrumentKind
    instrument_id: UUID
    revision_number: int
    supersedes_revision_id: UUID | None
    request_id: UUID
    request_fingerprint: str
    recorded_at: datetime
    manifest: SessionManifest
    source: SessionSourceProvenance
    manifest_json: str
    document_base64: str
    verification: Literal["MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"] = (
        "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    )


@dataclass(frozen=True, slots=True)
class SessionEvidenceRead:
    workspace_id: UUID
    instrument_kind: InstrumentKind
    instrument_id: UUID
    start_date: date
    end_date: date
    known_at: datetime
    revision_id: UUID | None
    supersedes_revision_id: UUID | None
    revision_number: int | None
    calendar_id: str | None
    calendar_version: str | None
    binding: SessionBinding | None
    coverage_start: date | None
    coverage_end: date | None
    evidence_status: Literal["ACTIVE", "WITHDRAWN"] | None
    days: tuple[SessionDay, ...]
    status: SessionReadStatus
    reasons: tuple[str, ...]
    missing_dates: tuple[date, ...]
    source: SessionSourceProvenance | None
    fingerprint: str
    recorded_at: datetime | None
    read_at: datetime
    verification: Literal["MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"] = (
        "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    )
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"


@dataclass(frozen=True, slots=True)
class SessionEvidenceCurrent:
    workspace_id: UUID
    instrument_kind: InstrumentKind
    instrument_id: UUID
    known_at: datetime
    revision_id: UUID | None
    supersedes_revision_id: UUID | None
    revision_number: int | None
    calendar_id: str | None
    calendar_version: str | None
    binding: SessionBinding | None
    coverage_start: date | None
    coverage_end: date | None
    evidence_status: Literal["ACTIVE", "WITHDRAWN"] | None
    source: SessionSourceProvenance | None
    recorded_at: datetime | None
    read_at: datetime
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    verification: Literal["MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"] = (
        "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    )
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"
