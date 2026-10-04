"""Versioned read contract shared by risk API, history and monitoring runtime."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.features.analysis.domain.product_comparison import ProductComparison, SynchronizedPricePair
from app.features.analysis.domain.risk_analytics import RiskMetrics
from app.features.market.service.risk_reference import RiskListingReference
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.domain.quote_quality import QuoteQuality
from app.features.position_monitoring.domain.risk_signals import RiskAssessment, RiskParameters
from app.features.product.service.risk_reference import RiskProductReference


@dataclass(frozen=True, slots=True)
class RiskConfiguration:
    revision: int
    enabled: bool
    parameters: RiskParameters
    configured_at: datetime | None = None
    actor: UUID | None = None
    policy_version: str = "POSITION_RISK_V1"


@dataclass(frozen=True, slots=True)
class PositionRiskView:
    trade_id: UUID
    position_id: UUID
    evaluated_at: datetime
    configuration: RiskConfiguration
    product: RiskProductReference | None
    listing: RiskListingReference | None
    metrics: RiskMetrics
    assessment: RiskAssessment
    quote_quality: QuoteQuality
    comparison: ProductComparison
    input_fingerprint: str
    basis_key: str
    input_prices: tuple[DailyPrice, ...]
    previous_snapshot_id: UUID | None = None
    snapshot_id: UUID | None = None
    quote_evidence: SavedQuoteEvidence | None = None
    comparison_inputs: tuple[SynchronizedPricePair, ...] = ()
    mode: str = "PREVIEW"
    execution_usable: bool = False
