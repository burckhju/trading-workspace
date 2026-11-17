"""Single-position read of original BID, owner currency and documented sessions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.domain.session_evidence import SessionEvidenceCurrent
from app.features.position_monitoring.domain.hebeltrader_original_bid import (
    DocumentedSessionMatch,
    OriginalBidAssessment,
)
from app.features.position_monitoring.domain.hebeltrader_product_price_scale import (
    ProductPriceScaleAssessment,
)
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    CompletedSessionCount,
    SessionEntry,
)
from app.features.position_monitoring.service.hebeltrader_session_contracts import SessionPeriodView
from app.features.trade_position.service.valuation_basis import PositionValuationBasis


@dataclass(frozen=True, slots=True)
class OriginalBidCheck:
    key: str
    label: str
    status: Literal["SATISFIED", "MISSING", "UNSUITABLE", "NOT_REACHED", "NOT_APPLICABLE"]
    detail: str
    reasons: tuple[str, ...]
    affected_rules: tuple[Literal["B04", "B58"], ...] = ("B04", "B58")


@dataclass(frozen=True, slots=True)
class ProductSessionPrerequisites:
    calendar: SessionEvidenceCurrent | None
    period: SessionPeriodView
    at_bid: DocumentedSessionMatch
    at_read: DocumentedSessionMatch
    interval_relation: Literal["SAME_INTERVAL", "DIFFERENT_INTERVALS", "NOT_ASSESSABLE"]


@dataclass(frozen=True, slots=True)
class UnderlyingSessionsAtBid:
    calendar: SessionEvidenceCurrent
    period: SessionPeriodView
    count: CompletedSessionCount | None


@dataclass(frozen=True, slots=True)
class HebeltraderOriginalBidReport:
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    position_state: Literal["OPEN", "CLOSED", "CANCELLED"]
    basis_id: str
    read_started_at: datetime
    read_completed_at: datetime
    evaluated_at: datetime
    economic_basis: PositionValuationBasis
    entry: SessionEntry | None
    saved_quote: SavedQuoteEvidence
    bid: OriginalBidAssessment
    product_price_scale: ProductPriceScaleAssessment
    product_sessions: ProductSessionPrerequisites
    underlying_sessions: UnderlyingSessionsAtBid
    coverage_status: Literal["PARTIAL", "UNSUITABLE", "NOT_APPLICABLE"]
    checks: tuple[OriginalBidCheck, ...]
    notices: tuple[str, ...]
    definition_version: Literal["hebeltrader-original-bid-v1"] = "hebeltrader-original-bid-v1"
    baseline_id: Literal["HEBELTRADER_CONFIRMED_BASELINE"] = "HEBELTRADER_CONFIRMED_BASELINE"
    baseline_version: Literal["1.0.0"] = "1.0.0"
    implementation_status: Literal["F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY"] = (
        "F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY"
    )
    rule_evaluation_status: Literal["B04_B05_B06_B58_NOT_EVALUATED"] = (
        "B04_B05_B06_B58_NOT_EVALUATED"
    )
    operation_status: Literal["NOT_ACTIVATED"] = "NOT_ACTIVATED"
    read_status: Literal["READ_ONLY"] = "READ_ONLY"
