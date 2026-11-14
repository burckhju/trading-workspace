"""Persistent target evidence without execution, stop or notification semantics.

The inputs are immutable projections of existing owners. A historical target
proof is distinct from the current availability of comparable observations.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

BASELINE_ID = "HEBELTRADER_CONFIRMED_BASELINE"
BASELINE_VERSION = "1.0.0"
DEFINITION_VERSION = "hebeltrader-targets-v1"
PROTECTION_BASIS_NOTICE = "Prüfgrundlage, noch kein bekanntgegebener Schutzvorschlag"

type TargetStatus = Literal["PROVEN", "NOT_PROVEN", "NOT_ASSESSABLE", "REVIEW_REQUIRED"]
type Assessability = Literal["ASSESSABLE", "NOT_ASSESSABLE"]
type GuidanceStatus = Literal[
    "NOT_TRIGGERED", "READY", "COVERED", "NOT_ASSESSABLE", "REVIEW_REQUIRED", "POSITION_CLOSED"
]


@dataclass(frozen=True, slots=True)
class TargetPositionBasis:
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    owner_basis_id: str
    opened_at: datetime | None
    opened_on: date | None
    opening_timezone: str | None
    remaining_quantity: int
    closed: bool
    option_direction: Literal["CALL", "PUT"] | None
    original_z1_quantity: int | None = None
    assigned_z1_sold_quantity: int | None = None
    personal_underlying_entry: Decimal | None = None
    personal_underlying_binding: PriceBinding | None = None
    evidence_revision_id: UUID | None = None
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class TargetSourceBasis:
    source_version_id: UUID
    binding: PriceBinding
    scale_reference: str | None
    reference_price: Decimal
    target_1: Decimal
    target_2: Decimal
    issue_date: date | None = None
    content_hash: str = ""


@dataclass(frozen=True, slots=True)
class TargetDailyEvidence:
    source_row_id: UUID
    fingerprint: str
    workspace_id: UUID
    listing_id: UUID
    trading_date: date
    high: Decimal
    currency: str
    interval_start: datetime | None
    interval_end: datetime | None
    issues: tuple[str, ...] = ()
    scale_status: str = "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION"
    time_precision: Literal["DATE_ONLY"] = field(default="DATE_ONLY", init=False)


@dataclass(frozen=True, slots=True)
class TargetHistoryBasis:
    workspace_id: UUID
    underlying_id: UUID
    fingerprint: str
    rows: tuple[TargetDailyEvidence, ...]
    listing_id: UUID | None
    binding: PriceBinding | None
    listing_fingerprint: str | None
    listing_timezone: str | None
    known_at: datetime
    status: Literal["AVAILABLE", "MISSING", "BLOCKED", "LIMIT_EXCEEDED"] = "AVAILABLE"
    reasons: tuple[str, ...] = ()
    stored_range_complete: bool = True
    intervals_complete: bool = True
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class TargetComparisonQualification:
    history_fingerprint: str
    listing_fingerprint: str
    source_version_id: UUID
    source_scale_reference: str
    evidence_reference: str


@dataclass(frozen=True, slots=True)
class TargetProof:
    assessment_id: UUID
    detected_at: datetime
    source: TargetSourceBasis
    entry_fingerprint: str
    option_direction: Literal["CALL"]
    evidence: TargetDailyEvidence
    history_fingerprint: str
    listing_fingerprint: str
    listing_timezone: str
    qualification: TargetComparisonQualification
    time_precision: Literal["DATE_ONLY"] = field(default="DATE_ONLY", init=False)


@dataclass(frozen=True, slots=True)
class TargetResult:
    target: Literal["Z1", "Z2"]
    event_id: UUID
    status: TargetStatus
    proof: TargetProof | None
    current_assessability: Assessability
    reasons: tuple[str, ...] = ()
    review_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Z1Orientation:
    status: GuidanceStatus
    original_quantity: int | None
    assigned_sold_quantity: int | None
    reasons: tuple[str, ...] = ()
    fraction: Decimal = field(default=Decimal("0.5"), init=False)


@dataclass(frozen=True, slots=True)
class RemainderExitReview:
    status: GuidanceStatus
    remaining_quantity: int | None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EntryProtectionBasis:
    status: GuidanceStatus
    personal_underlying_entry: Decimal | None
    binding: PriceBinding | None
    reasons: tuple[str, ...] = ()
    notice: str = field(default=PROTECTION_BASIS_NOTICE, init=False)


@dataclass(frozen=True, slots=True)
class TargetAssessment:
    assessment_id: UUID
    previous_assessment_id: UUID | None
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    owner_basis_id: str
    evidence_revision_id: UUID | None
    assessed_at: datetime
    input_fingerprint: str
    source_fingerprint: str | None
    entry_fingerprint: str
    z1: TargetResult
    z2: TargetResult
    z1_orientation: Z1Orientation
    z2_exit_review: RemainderExitReview
    protection_basis: EntryProtectionBasis
    guidance_priority: tuple[str, ...]
    baseline_id: str = BASELINE_ID
    baseline_version: str = BASELINE_VERSION
    definition_version: str = DEFINITION_VERSION


def _json_value(value: object) -> str:
    if isinstance(value, datetime):
        return (
            value.astimezone(UTC).isoformat()
            if value.utcoffset() is not None
            else value.isoformat()
        )
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported target evidence value: {type(value).__name__}")


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_value)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _event_id(position: TargetPositionBasis, target: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{BASELINE_ID}/{BASELINE_VERSION}/{position.workspace_id}/{position.position_id}/{target}",
    )


def _positive(value: Decimal | None) -> bool:
    return value is not None and value.is_finite() and value > 0


def _aware(value: datetime | None) -> bool:
    return value is not None and value.utcoffset() is not None


def _entry_boundary(position: TargetPositionBasis) -> tuple[datetime | None, tuple[str, ...]]:
    if position.opened_on is not None:
        if position.opened_at is not None:
            return None, ("ENTRY_TIME_PRECISION_CONFLICT",)
        if not position.opening_timezone:
            return None, ("ENTRY_TIMEZONE_MISSING",)
        try:
            zone = ZoneInfo(position.opening_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return None, ("ENTRY_TIMEZONE_INVALID",)
        return (
            datetime.combine(position.opened_on + timedelta(days=1), time.min, zone).astimezone(
                UTC
            ),
            (),
        )
    if not _aware(position.opened_at):
        return None, ("ENTRY_TIME_MISSING_OR_INVALID",)
    return position.opened_at, ()


def _closed(position: TargetPositionBasis) -> bool:
    return position.closed or position.cancelled or position.remaining_quantity == 0


def _comparison_problems(
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: TargetHistoryBasis,
    qualification: TargetComparisonQualification | None,
    assessed_at: datetime,
) -> tuple[str, ...]:
    problems: list[str] = []
    if _closed(position):
        problems.append("POSITION_CLOSED_OR_CANCELLED")
    if position.option_direction != "CALL":
        problems.append("PRODUCT_DIRECTION_NOT_SUPPORTED")
    if source is None:
        problems.append("SOURCE_BASIS_MISSING")
    else:
        if source.binding.basis is not PriceBasis.UNDERLYING or (
            source.binding.instrument_id != position.underlying_id
        ):
            problems.append("SOURCE_PRICE_BINDING_MISMATCH")
        if (
            not all(
                _positive(value)
                for value in (source.reference_price, source.target_1, source.target_2)
            )
            or not source.reference_price < source.target_1 < source.target_2
        ):
            problems.append("SOURCE_CALL_TARGET_ORDER_INVALID")
        if not source.scale_reference or not source.scale_reference.strip():
            problems.append("SOURCE_SCALE_REFERENCE_MISSING")
        if source.issue_date is None:
            problems.append("SOURCE_ISSUE_DATE_MISSING")
    if (history.workspace_id, history.underlying_id) != (
        position.workspace_id,
        position.underlying_id,
    ):
        problems.append("HISTORY_SCOPE_MISMATCH")
    if history.status != "AVAILABLE":
        problems.extend((f"HISTORY_{history.status}", *history.reasons))
    if not history.stored_range_complete:
        problems.append("STORED_HISTORY_RANGE_INCOMPLETE")
    if history.listing_id is None or history.binding is None or not history.listing_fingerprint:
        problems.append("HISTORICAL_LISTING_BINDING_MISSING")
    elif source is not None and history.binding != source.binding:
        problems.append("HISTORY_PRICE_BINDING_MISMATCH")
    if not history.listing_timezone:
        problems.append("LISTING_TIMEZONE_MISSING")
    else:
        try:
            ZoneInfo(history.listing_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            problems.append("LISTING_TIMEZONE_INVALID")
    if not _aware(history.known_at) or history.known_at > assessed_at:
        problems.append("HISTORY_CUTOFF_INVALID")
    if qualification is None:
        problems.append("PRICE_COMPARISON_NOT_CONFIRMED")
    else:
        if qualification.history_fingerprint != history.fingerprint:
            problems.append("COMPARISON_HISTORY_FINGERPRINT_MISMATCH")
        if qualification.listing_fingerprint != history.listing_fingerprint:
            problems.append("COMPARISON_LISTING_FINGERPRINT_MISMATCH")
        if source is None or qualification.source_version_id != source.source_version_id:
            problems.append("COMPARISON_SOURCE_VERSION_MISMATCH")
        if source is None or qualification.source_scale_reference != source.scale_reference:
            problems.append("COMPARISON_SCALE_REFERENCE_MISMATCH")
        if not qualification.evidence_reference.strip():
            problems.append("COMPARISON_EVIDENCE_REFERENCE_MISSING")
    return tuple(dict.fromkeys(problems))


def _usable_rows(
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: TargetHistoryBasis,
    qualification: TargetComparisonQualification | None,
    assessed_at: datetime,
) -> tuple[tuple[TargetDailyEvidence, ...], tuple[str, ...]]:
    boundary, entry_problems = _entry_boundary(position)
    problems = _comparison_problems(position, source, history, qualification, assessed_at)
    if entry_problems or problems:
        return (), (*entry_problems, *problems)
    assert boundary is not None and history.listing_timezone is not None
    assert source is not None and source.issue_date is not None
    zone = ZoneInfo(history.listing_timezone)
    # A date with unknown publisher zone spans the global UTC+14 ... UTC-12
    # envelope. This is its latest possible end, not an invented publication
    # clock, and is independent of the listing's timezone or import timestamps.
    publication_latest_end = datetime.combine(
        source.issue_date + timedelta(days=1), time(hour=12), UTC
    )
    rows: list[TargetDailyEvidence] = []
    skipped: list[str] = []
    originals: dict[UUID, TargetDailyEvidence] = {}
    duplicates: set[UUID] = set()
    for row in history.rows:
        if row.source_row_id in originals and originals[row.source_row_id] != row:
            duplicates.add(row.source_row_id)
        else:
            originals[row.source_row_id] = row
    seen: set[UUID] = set()
    for row in history.rows:
        if row.source_row_id in seen:
            continue
        seen.add(row.source_row_id)
        if row.source_row_id in duplicates:
            skipped.append("CONFLICTING_ORIGINAL_PRICE_EVIDENCE")
            continue
        if (row.workspace_id, row.listing_id, row.currency) != (
            position.workspace_id,
            history.listing_id,
            source.binding.currency,
        ):
            skipped.append("ROW_SCOPE_OR_CURRENCY_MISMATCH")
            continue
        if row.issues:
            skipped.extend(("ROW_EVIDENCE_UNSUITABLE", *row.issues))
            continue
        if row.scale_status != "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION":
            skipped.append("ROW_ADJUSTMENT_REQUIRES_OWNER_EVIDENCE")
            continue
        if not _positive(row.high) or not row.fingerprint:
            skipped.append("ROW_ORIGINAL_VALUES_INVALID")
            continue
        expected_start = datetime.combine(row.trading_date, time.min, zone).astimezone(UTC)
        expected_end = datetime.combine(
            row.trading_date + timedelta(days=1), time.min, zone
        ).astimezone(UTC)
        if (
            not _aware(row.interval_start)
            or not _aware(row.interval_end)
            or row.interval_start != expected_start
            or row.interval_end != expected_end
        ):
            skipped.append("FULL_DAILY_INTERVAL_NOT_ESTABLISHED")
            continue
        if expected_end > min(history.known_at, assessed_at):
            skipped.append("FULL_DAILY_INTERVAL_NOT_COMPLETED")
            continue
        if (history.start_date is not None and row.trading_date < history.start_date) or (
            history.end_date is not None and row.trading_date > history.end_date
        ):
            skipped.append("ROW_OUTSIDE_REQUESTED_RANGE")
            continue
        if expected_start < boundary:
            skipped.append("INTERVAL_NOT_ENTIRELY_AFTER_ENTRY")
            continue
        if expected_start < publication_latest_end:
            skipped.append("SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED")
            continue
        rows.append(row)
    if not rows:
        skipped.append("NO_SUITABLE_POST_ENTRY_DAILY_EVIDENCE")
    return tuple(sorted(rows, key=lambda row: (row.trading_date, row.source_row_id))), tuple(
        dict.fromkeys(skipped)
    )


def _review_problems(
    previous: TargetResult,
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: TargetHistoryBasis,
    entry_fingerprint: str,
) -> tuple[str, ...]:
    proof = previous.proof
    if proof is None:
        return previous.review_reasons if previous.status == "REVIEW_REQUIRED" else ()
    problems = list(previous.review_reasons) if previous.status == "REVIEW_REQUIRED" else []
    if source is None:
        problems.append("PROVEN_SOURCE_BASIS_UNAVAILABLE")
    elif _fingerprint(asdict(proof.source)) != _fingerprint(asdict(source)):
        problems.append("PROVEN_SOURCE_BASIS_CHANGED")
    if proof.entry_fingerprint != entry_fingerprint:
        problems.append("PROVEN_ENTRY_TIME_BASIS_CHANGED")
    if position.option_direction != proof.option_direction:
        problems.append("PROVEN_PRODUCT_DIRECTION_CHANGED")
    if (history.workspace_id, history.underlying_id) == (
        position.workspace_id,
        position.underlying_id,
    ):
        if (
            history.listing_id == proof.evidence.listing_id
            and history.listing_fingerprint is not None
            and history.listing_fingerprint != proof.listing_fingerprint
        ):
            problems.append("PROVEN_LISTING_BASIS_CHANGED")
        originals = tuple(
            row for row in history.rows if row.source_row_id == proof.evidence.source_row_id
        )
        if originals and any(row != proof.evidence for row in originals):
            problems.append("ORIGINAL_PRICE_EVIDENCE_CHANGED")
        elif not originals and any(
            (row.listing_id, row.trading_date)
            == (proof.evidence.listing_id, proof.evidence.trading_date)
            for row in history.rows
        ):
            problems.append("ORIGINAL_PRICE_EVIDENCE_REPLACED")
    if previous.status == "REVIEW_REQUIRED" and not problems:
        problems.append("PRIOR_REVIEW_REQUIRED")
    return tuple(dict.fromkeys(problems))


def _target_result(
    *,
    target: Literal["Z1", "Z2"],
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: TargetHistoryBasis,
    qualification: TargetComparisonQualification | None,
    rows: tuple[TargetDailyEvidence, ...],
    reasons: tuple[str, ...],
    assessment_id: UUID,
    assessed_at: datetime,
    entry_fingerprint: str,
    previous: TargetResult | None,
) -> TargetResult:
    assessability: Assessability = "ASSESSABLE" if rows else "NOT_ASSESSABLE"
    review = (
        _review_problems(previous, position, source, history, entry_fingerprint) if previous else ()
    )
    if review:
        return TargetResult(
            target,
            _event_id(position, target),
            "REVIEW_REQUIRED",
            previous.proof if previous else None,
            assessability,
            reasons,
            review,
        )
    if previous is not None and previous.proof is not None:
        return TargetResult(
            target, _event_id(position, target), "PROVEN", previous.proof, assessability, reasons
        )
    proof = None
    if rows:
        assert source is not None and qualification is not None
        assert history.listing_fingerprint is not None and history.listing_timezone is not None
        threshold = source.target_1 if target == "Z1" else source.target_2
        hit = next((row for row in rows if row.high >= threshold), None)
        if hit is not None:
            proof = TargetProof(
                assessment_id,
                assessed_at,
                source,
                entry_fingerprint,
                "CALL",
                hit,
                history.fingerprint,
                history.listing_fingerprint,
                history.listing_timezone,
                qualification,
            )
    return TargetResult(
        target,
        _event_id(position, target),
        "PROVEN" if proof else "NOT_PROVEN" if rows else "NOT_ASSESSABLE",
        proof,
        assessability,
        reasons,
    )


def _guidance_status(position: TargetPositionBasis, target: TargetResult) -> GuidanceStatus:
    if _closed(position):
        return "POSITION_CLOSED"
    if target.status == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if target.status == "NOT_ASSESSABLE":
        return "NOT_ASSESSABLE"
    return "READY" if target.status == "PROVEN" else "NOT_TRIGGERED"


def _orientation(position: TargetPositionBasis, z1: TargetResult) -> Z1Orientation:
    status = _guidance_status(position, z1)
    reasons: list[str] = []
    original = position.original_z1_quantity
    sold = position.assigned_z1_sold_quantity
    if status == "READY":
        if original is None or isinstance(original, bool) or original <= 0:
            status = "NOT_ASSESSABLE"
            reasons.append("ORIGINAL_Z1_QUANTITY_MISSING_OR_INVALID")
        if sold is None or isinstance(sold, bool) or sold < 0:
            status = "NOT_ASSESSABLE"
            reasons.append("Z1_SALE_ATTRIBUTION_MISSING_OR_INVALID")
        if status == "READY" and original is not None and sold is not None:
            # Compare the reported facts to the orientation; never derive a
            # rounded sale/order quantity, nor halve the current remainder.
            status = "COVERED" if sold * 2 >= original else "READY"
    return Z1Orientation(status, original, sold, tuple(reasons))


def _protection(position: TargetPositionBasis, z1: TargetResult) -> EntryProtectionBasis:
    status = _guidance_status(position, z1)
    reasons: tuple[str, ...] = ()
    value = None
    binding = None
    if status == "READY":
        if not _positive(position.personal_underlying_entry):
            status = "NOT_ASSESSABLE"
            reasons = ("PERSONAL_UNDERLYING_ENTRY_MISSING_OR_INVALID",)
        elif z1.proof is None or position.personal_underlying_binding != z1.proof.source.binding:
            status = "NOT_ASSESSABLE"
            reasons = ("PERSONAL_UNDERLYING_BINDING_MISMATCH",)
        else:
            value = position.personal_underlying_entry
            binding = position.personal_underlying_binding
    return EntryProtectionBasis(status, value, binding, reasons)


def evaluate_hebeltrader_targets(
    *,
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: TargetHistoryBasis,
    qualification: TargetComparisonQualification | None,
    assessment_id: UUID,
    assessed_at: datetime,
    previous: TargetAssessment | None = None,
) -> TargetAssessment:
    """Assess target evidence without generating orders or announced stop marks."""
    if not _aware(assessed_at):
        raise ValueError("ASSESSMENT_TIME_MUST_BE_AWARE")
    if isinstance(position.remaining_quantity, bool) or position.remaining_quantity < 0:
        raise ValueError("INVALID_OWNER_REMAINING_QUANTITY")
    if previous is not None:
        if (previous.workspace_id, previous.trade_id, previous.position_id) != (
            position.workspace_id,
            position.trade_id,
            position.position_id,
        ):
            raise ValueError("PREVIOUS_ASSESSMENT_SCOPE_MISMATCH")
        if (previous.baseline_id, previous.baseline_version, previous.definition_version) != (
            BASELINE_ID,
            BASELINE_VERSION,
            DEFINITION_VERSION,
        ):
            raise ValueError("PREVIOUS_ASSESSMENT_VERSION_MISMATCH")
        if previous.assessment_id == assessment_id or previous.assessed_at > assessed_at:
            raise ValueError("ASSESSMENT_PREDECESSOR_INVALID")
        for key, result in (("Z1", previous.z1), ("Z2", previous.z2)):
            if result.target != key or result.event_id != _event_id(position, key):
                raise ValueError("PREVIOUS_TARGET_IDENTITY_MISMATCH")
    entry_fingerprint = _fingerprint(
        {
            "opened_at": position.opened_at,
            "opened_on": position.opened_on,
            "opening_timezone": position.opening_timezone,
        }
    )
    source_fingerprint = _fingerprint(asdict(source)) if source is not None else None
    input_fingerprint = _fingerprint(
        {
            "definition": DEFINITION_VERSION,
            "position": asdict(position),
            "source": asdict(source) if source else None,
            "history_fingerprint": history.fingerprint,
            "listing_fingerprint": history.listing_fingerprint,
            "qualification": asdict(qualification) if qualification else None,
        }
    )
    rows, reasons = _usable_rows(position, source, history, qualification, assessed_at)
    previous_results: tuple[tuple[Literal["Z1", "Z2"], TargetResult | None], ...] = (
        ("Z1", previous.z1 if previous else None),
        ("Z2", previous.z2 if previous else None),
    )
    z1, z2 = tuple(
        _target_result(
            target=key,
            previous=prior,
            position=position,
            source=source,
            history=history,
            qualification=qualification,
            rows=rows,
            reasons=reasons,
            assessment_id=assessment_id,
            assessed_at=assessed_at,
            entry_fingerprint=entry_fingerprint,
        )
        for key, prior in previous_results
    )
    orientation = _orientation(position, z1)
    exit_status = _guidance_status(position, z2)
    exit_review = RemainderExitReview(
        exit_status, position.remaining_quantity if exit_status == "READY" else None
    )
    protection = _protection(position, z1)
    priority = tuple(
        rule
        for rule, status in (
            ("B03", exit_review.status),
            ("B01", orientation.status),
            ("B02", protection.status),
        )
        if status == "READY"
    )
    return TargetAssessment(
        assessment_id,
        previous.assessment_id if previous else None,
        position.workspace_id,
        position.trade_id,
        position.position_id,
        position.owner_basis_id,
        position.evidence_revision_id,
        assessed_at,
        input_fingerprint,
        source_fingerprint,
        entry_fingerprint,
        z1,
        z2,
        orientation,
        exit_review,
        protection,
        priority,
    )
