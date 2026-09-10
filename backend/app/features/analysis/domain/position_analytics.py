"""Deterministic position-management analytics built on the governed FT-006 baseline."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from app.features.analysis.domain.calculator import calculate
from app.features.analysis.domain.models import AnalysisComputation, AnalysisParameters, SnapshotRow

INDICATOR_SET_VERSION = "POSITION_ANALYTICS_V1"


def _true_range(row: SnapshotRow, previous_close: Decimal) -> Decimal:
    return max(
        row.high - row.low,
        abs(row.high - previous_close),
        abs(row.low - previous_close),
    )


def _rsi14(closes: list[Decimal]) -> Decimal:
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous, current in zip(closes[-15:-1], closes[-14:], strict=True):
        change = current - previous
        gains.append(max(change, Decimal(0)))
        losses.append(max(-change, Decimal(0)))
    average_gain = sum(gains, Decimal(0)) / Decimal(14)
    average_loss = sum(losses, Decimal(0)) / Decimal(14)
    if average_loss == 0:
        return Decimal(100) if average_gain > 0 else Decimal(50)
    relative_strength = average_gain / average_loss
    return Decimal(100) - Decimal(100) / (Decimal(1) + relative_strength)


def calculate_position_analytics(
    parameters: AnalysisParameters,
    rows: tuple[SnapshotRow, ...],
) -> AnalysisComputation:
    """Extend the governed baseline output without changing its runtime identity."""
    baseline = calculate(parameters, rows)
    if not baseline.metrics:
        return baseline

    q = Decimal(1).scaleb(-parameters.rounding_scale)

    def rounded(value: Decimal) -> Decimal:
        return value.quantize(q, rounding=ROUND_HALF_EVEN)

    selected = [
        row.close if parameters.price_field.value == "CLOSE" else row.adjusted_close
        for row in rows
    ]
    closes = [value for value in selected if value is not None]
    atr14 = sum(
        (
            _true_range(rows[index], rows[index - 1].close)
            for index in range(len(rows) - 14, len(rows))
        ),
        Decimal(0),
    ) / Decimal(14)

    metrics = dict(baseline.metrics)
    metrics.update(
        {
            "atr_14": str(rounded(atr14)),
            "rsi_14": str(rounded(_rsi14(closes))),
            "highest_high_20": str(rounded(max(row.high for row in rows[-20:]))),
            "indicator_set_version": INDICATOR_SET_VERSION,
        }
    )
    return AnalysisComputation(
        metrics=metrics,
        criteria=baseline.criteria,
        notes=baseline.notes,
        quality_status=baseline.quality_status,
    )
