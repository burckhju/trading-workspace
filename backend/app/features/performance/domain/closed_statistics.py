"""Statistics consume one complete closed report; they never project executions.

The existing source fingerprint binds the inherited Decimal precision and
rounding. All additional arithmetic uses a local copy of that context. The
statistics definition fixes operation order and display rounding independently
of the unchanged financial/source definition.
"""

from decimal import Decimal, localcontext

from app.features.performance.domain.closed_models import (
    ClosedTradeCounts,
    ClosedTradeItem,
    ClosedTradeStatistic,
    ClosedTradeStatistics,
)
from app.features.performance.domain.models import ReportSummary
from app.features.performance.domain.report import decimal_string, displayed

DEFINITION_VERSION = "closed-trade-statistics-v1"


def _value(value: Decimal, minor_unit: int) -> ClosedTradeStatistic:
    return ClosedTradeStatistic(
        raw=decimal_string(value), display=displayed(value, minor_unit), reason=None
    )


def build_closed_statistics(
    *,
    summary: ReportSummary,
    counts: ClosedTradeCounts,
    items: tuple[ClosedTradeItem, ...],
    minor_unit: int,
    report_basis_id: str,
) -> ClosedTradeStatistics:
    """Derive all four values from the already qualified, unrounded owner results."""
    if summary.status != "COMPLETE" or counts.qualified == 0:
        empty = summary.status == "EMPTY"
        unavailable = ClosedTradeStatistic(
            raw=None,
            display=None,
            reason=(
                "Keine abgeschlossenen Trades in der Auswahl"
                if empty
                else "Berichtsgrundlage unvollständig"
            ),
        )
        return ClosedTradeStatistics(
            definition_version=DEFINITION_VERSION,
            report_basis_id=report_basis_id,
            report_status=summary.status,
            population=0 if empty else None,
            win_rate=unavailable,
            average_gross_pnl=unavailable,
            median_gross_pnl=unavailable,
            gross_profit_factor=unavailable,
        )

    # A missing qualified amount indicates an inconsistent producer, never zero.
    raw_values = [item.realized_gross_pnl for item in items if item.group == "QUALIFIED"]
    if summary.total is None or len(raw_values) != counts.qualified or None in raw_values:
        raise ValueError("Complete trade statistics require all qualified amounts")

    with localcontext():
        values = [Decimal(value) for value in raw_values if value is not None]
        total = Decimal(summary.total)
        if not total.is_finite() or not all(value.is_finite() for value in values):
            raise ValueError("Complete trade statistics require finite amounts")
        population = Decimal(counts.qualified)
        win_rate = Decimal(counts.positive) / population * Decimal(100)
        # Reuse the established finite-context sum, including its operation order.
        average = total / population
        ordered = sorted(values)
        middle = len(ordered) // 2
        median = (
            ordered[middle]
            if len(ordered) % 2
            else (ordered[middle - 1] + ordered[middle]) / Decimal(2)
        )
        gains = sum((value for value in values if value > 0), Decimal(0))
        losses = sum((value for value in values if value < 0), Decimal(0))
        profit_factor = (
            _value(gains / losses.copy_abs(), 2)
            if losses != 0
            else ClosedTradeStatistic(
                raw=None, display=None, reason="Nicht definiert: keine Verlusttrades"
            )
        )
        return ClosedTradeStatistics(
            definition_version=DEFINITION_VERSION,
            report_basis_id=report_basis_id,
            report_status=summary.status,
            population=counts.qualified,
            win_rate=_value(win_rate, 2),
            average_gross_pnl=_value(average, minor_unit),
            median_gross_pnl=_value(median, minor_unit),
            gross_profit_factor=profit_factor,
        )
