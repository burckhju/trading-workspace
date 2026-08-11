"""Transparent, deterministic top-down analysis models for Sprint 5."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)

RELATIVE_STRENGTH_MODEL_ID = "RELATIVE_STRENGTH"
RELATIVE_STRENGTH_MODEL_VERSION = "1.0.0"
MARKET_CONTEXT_MODEL_ID = "MARKET_CONTEXT"
MARKET_CONTEXT_MODEL_VERSION = "1.0.0"


class TradingDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class ContextClassification(StrEnum):
    FAVORABLE = "FAVORABLE"
    NEUTRAL = "NEUTRAL"
    CAUTIOUS = "CAUTIOUS"
    UNFAVORABLE = "UNFAVORABLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


@dataclass(frozen=True, slots=True)
class RelativeStrengthParameters:
    """V1 model parameters approved for the top-down workflow."""

    window: int = 60
    neutral_zone: Decimal = Decimal("0.02")
    rounding_scale: int = 6

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError("window must be positive")
        if self.neutral_zone < 0:
            raise ValueError("neutral_zone must not be negative")
        if self.rounding_scale < 0 or self.rounding_scale > 12:
            raise ValueError("rounding_scale must be between 0 and 12")


@dataclass(frozen=True, slots=True)
class RelativeStrengthResult:
    model_id: str
    model_version: str
    window: int
    neutral_zone: Decimal
    subject_return: Decimal | None
    reference_return: Decimal | None
    relative_performance: Decimal | None
    classification: CriterionClassification
    quality_status: AnalysisQualityStatus
    explanation: str


def calculate_relative_strength(
    subject_prices: tuple[Decimal, ...],
    reference_prices: tuple[Decimal, ...],
    parameters: RelativeStrengthParameters | None = None,
) -> RelativeStrengthResult:
    """Compare equal-window returns using the approved V1 return-difference model."""

    parameters = parameters or RelativeStrengthParameters()
    required = parameters.window + 1
    if len(subject_prices) < required or len(reference_prices) < required:
        return RelativeStrengthResult(
            RELATIVE_STRENGTH_MODEL_ID,
            RELATIVE_STRENGTH_MODEL_VERSION,
            parameters.window,
            parameters.neutral_zone,
            None,
            None,
            None,
            CriterionClassification.NOT_EVALUABLE,
            AnalysisQualityStatus.INSUFFICIENT,
            f"At least {required} aligned observations are required",
        )
    subject_start, subject_end = subject_prices[-required], subject_prices[-1]
    reference_start, reference_end = reference_prices[-required], reference_prices[-1]
    if subject_start <= 0 or reference_start <= 0:
        return RelativeStrengthResult(
            RELATIVE_STRENGTH_MODEL_ID,
            RELATIVE_STRENGTH_MODEL_VERSION,
            parameters.window,
            parameters.neutral_zone,
            None,
            None,
            None,
            CriterionClassification.NOT_EVALUABLE,
            AnalysisQualityStatus.INSUFFICIENT,
            "Start prices must be positive",
        )
    q = Decimal(1).scaleb(-parameters.rounding_scale)
    subject_return = (subject_end / subject_start - Decimal(1)).quantize(
        q, rounding=ROUND_HALF_EVEN
    )
    reference_return = (reference_end / reference_start - Decimal(1)).quantize(
        q, rounding=ROUND_HALF_EVEN
    )
    relative = (subject_return - reference_return).quantize(q, rounding=ROUND_HALF_EVEN)
    if relative > parameters.neutral_zone:
        classification = CriterionClassification.POSITIVE
    elif relative < -parameters.neutral_zone:
        classification = CriterionClassification.NEGATIVE
    else:
        classification = CriterionClassification.NEUTRAL
    return RelativeStrengthResult(
        RELATIVE_STRENGTH_MODEL_ID,
        RELATIVE_STRENGTH_MODEL_VERSION,
        parameters.window,
        parameters.neutral_zone,
        subject_return,
        reference_return,
        relative,
        classification,
        AnalysisQualityStatus.GOOD,
        "Return(subject, window) - Return(reference, window)",
    )


@dataclass(frozen=True, slots=True)
class MarketContextResult:
    model_id: str
    model_version: str
    direction: TradingDirection
    long_trend: CriterionClassification
    medium_trend: CriterionClassification
    short_trend: CriterionClassification
    classification: ContextClassification
    quality_status: AnalysisQualityStatus
    warnings: tuple[str, ...]
    explanation: str


def calculate_market_context(
    *,
    direction: TradingDirection,
    long_trend: CriterionClassification,
    medium_trend: CriterionClassification,
    short_trend: CriterionClassification,
    quality_status: AnalysisQualityStatus = AnalysisQualityStatus.GOOD,
) -> MarketContextResult:
    """Classify the primary benchmark using the approved V1 trend hierarchy."""

    values = (long_trend, medium_trend, short_trend)
    if quality_status is AnalysisQualityStatus.INSUFFICIENT or any(
        value is CriterionClassification.NOT_EVALUABLE for value in values[:2]
    ):
        classification = ContextClassification.NOT_EVALUABLE
        warnings: tuple[str, ...] = ()
    else:
        expected = (
            CriterionClassification.POSITIVE
            if direction is TradingDirection.LONG
            else CriterionClassification.NEGATIVE
        )
        opposite = (
            CriterionClassification.NEGATIVE
            if direction is TradingDirection.LONG
            else CriterionClassification.POSITIVE
        )
        if long_trend is opposite or medium_trend is opposite:
            classification = ContextClassification.UNFAVORABLE
            warnings = ()
        elif long_trend is expected and medium_trend is expected:
            if short_trend is opposite:
                classification = ContextClassification.CAUTIOUS
                warnings = ("Short-term benchmark trend opposes the requested direction",)
            else:
                classification = ContextClassification.FAVORABLE
                warnings = ()
        else:
            classification = ContextClassification.NEUTRAL
            warnings = ()
        if quality_status is AnalysisQualityStatus.LIMITED:
            warnings = (*warnings, "Benchmark analysis quality is LIMITED")
    return MarketContextResult(
        MARKET_CONTEXT_MODEL_ID,
        MARKET_CONTEXT_MODEL_VERSION,
        direction,
        long_trend,
        medium_trend,
        short_trend,
        classification,
        quality_status,
        warnings,
        "Long and medium trend determine structure; short trend may downgrade to CAUTIOUS",
    )
