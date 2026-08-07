"""Pure deterministic FT-006 trend and momentum model V1."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from math import log, sqrt

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
    PriceField,
)
from app.features.analysis.domain.models import (
    AnalysisComputation,
    AnalysisParameters,
    CriterionResult,
    SnapshotRow,
)

MODEL_ID = "EOD_TREND_MOMENTUM"
MODEL_VERSION = "1.0.0"


def _classification(
    value: Decimal | None, threshold: Decimal = Decimal("0.01")
) -> CriterionClassification:
    if value is None:
        return CriterionClassification.NOT_EVALUABLE
    if value > threshold:
        return CriterionClassification.POSITIVE
    if value < -threshold:
        return CriterionClassification.NEGATIVE
    return CriterionClassification.NEUTRAL


def calculate(parameters: AnalysisParameters, rows: tuple[SnapshotRow, ...]) -> AnalysisComputation:
    notes: list[str] = []
    selected: list[Decimal] = []
    for row in rows:
        value = row.close if parameters.price_field is PriceField.CLOSE else row.adjusted_close
        if value is None:
            notes.append(f"{row.trading_date.isoformat()}: adjusted close missing")
            continue
        selected.append(value)
    if len(selected) < parameters.minimum_required_observations:
        return AnalysisComputation(
            metrics={},
            criteria=(
                CriterionResult(
                    "DATA_COMPLETENESS",
                    CriterionClassification.NOT_EVALUABLE,
                    Decimal(len(selected)),
                    "Insufficient observations",
                ),
            ),
            notes=(
                *notes,
                (
                    f"Required {parameters.minimum_required_observations}, "
                    f"available {len(selected)}"
                ),
            ),
            quality_status=AnalysisQualityStatus.INSUFFICIENT,
        )
    q = Decimal(1).scaleb(-parameters.rounding_scale)

    def rounded(value: Decimal) -> Decimal:
        return value.quantize(q, rounding=ROUND_HALF_EVEN)

    def sma(window: int) -> Decimal:
        return sum(selected[-window:], Decimal(0)) / Decimal(window)

    latest = selected[-1]
    metrics: dict[str, str | None] = {"latest_price": str(rounded(latest))}
    criteria: list[CriterionResult] = []
    for name, window in (
        ("SHORT_TREND", parameters.short_window),
        ("MEDIUM_TREND", parameters.medium_window),
        ("LONG_TREND", parameters.long_window),
    ):
        average = sma(window)
        distance = latest / average - Decimal(1)
        metrics[f"sma_{window}"] = str(rounded(average))
        metrics[f"distance_sma_{window}"] = str(rounded(distance))
        criteria.append(
            CriterionResult(
                name,
                _classification(distance),
                rounded(distance),
                f"Latest price relative to SMA {window}",
            )
        )
    for window in parameters.momentum_windows:
        momentum = latest / selected[-window - 1] - Decimal(1) if len(selected) > window else None
        metrics[f"momentum_{window}"] = None if momentum is None else str(rounded(momentum))
        criteria.append(
            CriterionResult(
                f"MOMENTUM_{window}",
                _classification(momentum),
                None if momentum is None else rounded(momentum),
                f"Return over {window} observations",
            )
        )
    returns = [
        log(float(selected[i] / selected[i - 1]))
        for i in range(len(selected) - parameters.volatility_window, len(selected))
    ]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(len(returns) - 1, 1)
    with localcontext() as ctx:
        ctx.prec = 28
        volatility = Decimal(str(sqrt(variance))) * parameters.annualization_factor.sqrt()
    metrics["annualized_volatility"] = str(rounded(volatility))
    criteria.append(
        CriterionResult(
            "VOLATILITY",
            CriterionClassification.NEUTRAL,
            rounded(volatility),
            "Annualized realized volatility; descriptive only",
        )
    )
    range_rows = rows[-parameters.range_window :]
    period_high = max(row.high for row in range_rows)
    period_low = min(row.low for row in range_rows)
    position = (
        (latest - period_low) / (period_high - period_low)
        if period_high != period_low
        else Decimal("0.5")
    )
    metrics.update(
        {
            "period_high": str(rounded(period_high)),
            "period_low": str(rounded(period_low)),
            "range_position": str(rounded(position)),
        }
    )
    range_class = (
        CriterionClassification.POSITIVE
        if position >= Decimal("0.66")
        else (
            CriterionClassification.NEGATIVE
            if position <= Decimal("0.33")
            else CriterionClassification.NEUTRAL
        )
    )
    criteria.append(
        CriterionResult(
            "RANGE_POSITION",
            range_class,
            rounded(position),
            "Position within observed high-low range",
        )
    )
    quality = (
        AnalysisQualityStatus.LIMITED
        if notes or any(row.quality_status != "GOOD" for row in rows)
        else AnalysisQualityStatus.GOOD
    )
    return AnalysisComputation(
        metrics=metrics,
        criteria=tuple(criteria),
        notes=tuple(notes),
        quality_status=quality,
    )
