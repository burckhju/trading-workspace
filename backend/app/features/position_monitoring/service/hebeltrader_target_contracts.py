"""Narrow persisted-input target read, separate from baseline activation."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
    TargetStatus,
)

type BasisStatus = Literal["AVAILABLE", "NOT_ASSESSABLE", "NOT_APPLICABLE"]


@dataclass(frozen=True, slots=True)
class TargetEvidenceView:
    trading_date: date
    interval_start: datetime
    interval_end: datetime
    high: Decimal
    source_row_id: UUID
    source_fingerprint: str
    provider: str
    provider_symbol: str
    listing_id: UUID
    time_precision: Literal["DATE_ONLY"]
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class TargetView:
    target: Literal["Z1", "Z2"]
    status: TargetStatus
    threshold: Decimal | None
    currency: str | None
    event_id: UUID | None
    proof_source_version_id: UUID | None
    proof_scale_reference: str | None
    detail: str
    reasons: tuple[str, ...]
    evidence: TargetEvidenceView | None


@dataclass(frozen=True, slots=True)
class OrientationView:
    status: BasisStatus
    original_quantity: int | None
    assigned_sold_quantity: int | None
    detail: str
    proportion: Literal["0.5"] = "0.5"


@dataclass(frozen=True, slots=True)
class ProtectionBasisView:
    status: BasisStatus
    personal_underlying_entry: Decimal | None
    currency: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class TargetAssessmentView:
    id: UUID
    recorded_at: datetime
    basis_id: str
    source_version_id: UUID | None
    previous_assessment_id: UUID | None
    targets: tuple[TargetView, ...]
    orientation: OrientationView
    protection_basis: ProtectionBasisView


@dataclass(frozen=True, slots=True)
class TargetInputsView:
    source_version_id: UUID | None
    source_scale_reference: str | None
    price_history_fingerprint: str
    listing_binding_fingerprint: str | None
    qualification_reusable: bool
    available_price_rows: int
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HebeltraderTargetsReport:
    trade_id: UUID
    position_id: UUID
    current_basis_id: str
    currentness: Literal["CURRENT", "CHANGED_INPUTS", "NO_ASSESSMENT"]
    position_state: Literal["OPEN", "CLOSED", "CANCELLED"]
    read_started_at: datetime
    read_completed_at: datetime
    assessment_count: int
    inputs: TargetInputsView
    latest_assessment: TargetAssessmentView | None
    definition_version: Literal["hebeltrader-targets-v1"] = "hebeltrader-targets-v1"
    baseline_id: Literal["HEBELTRADER_CONFIRMED_BASELINE"] = "HEBELTRADER_CONFIRMED_BASELINE"
    baseline_version: Literal["1.0.0"] = "1.0.0"
    implementation_status: Literal["F207_2_TARGET_HISTORY_ONLY"] = "F207_2_TARGET_HISTORY_ONLY"
    operation_status: Literal["NOT_ACTIVATED"] = "NOT_ACTIVATED"


@dataclass(frozen=True, slots=True)
class TargetAssessmentCommand:
    position_id: UUID
    request_id: UUID
    expected_basis_id: str
    expected_assessment_id: UUID | None
    qualification: TargetComparisonQualification | None = None
