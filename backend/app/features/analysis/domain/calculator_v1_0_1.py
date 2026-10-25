"""Explicit FT-006 1.0.1 source-quality policy over the frozen V1 arithmetic.

VALID is the persisted price-owner vocabulary, not the analysis result GOOD.
Never rewrite source rows, historical results, or the released 1.0.0 policy.
Time-relative freshness remains the application owner's responsibility.
"""

from __future__ import annotations

from dataclasses import replace

from app.features.analysis.domain.calculator import MODEL_ID as MODEL_ID
from app.features.analysis.domain.calculator import calculate as calculate_legacy
from app.features.analysis.domain.enums import AnalysisQualityStatus
from app.features.analysis.domain.models import (
    AnalysisComputation,
    AnalysisParameters,
    SnapshotRow,
)

MODEL_VERSION = "1.0.1"


def calculate(parameters: AnalysisParameters, rows: tuple[SnapshotRow, ...]) -> AnalysisComputation:
    """Recompute quality from unchanged source facts, retaining numeric semantics."""
    computation = calculate_legacy(parameters, rows)
    notes = list(computation.notes)
    for row in rows:
        if row.quality_status != "VALID":
            notes.append(
                f"{row.trading_date.isoformat()}: source quality is {row.quality_status!r}, "
                "expected VALID"
            )
        for warning in row.warnings:
            # Even an empty/malformed warning is not evidence of a clean input.
            notes.append(f"{row.trading_date.isoformat()}: source warning: {warning}")
    if computation.quality_status is AnalysisQualityStatus.INSUFFICIENT:
        quality = AnalysisQualityStatus.INSUFFICIENT
    elif notes:
        quality = AnalysisQualityStatus.LIMITED
    else:
        quality = AnalysisQualityStatus.GOOD
    return replace(computation, quality_status=quality, notes=tuple(notes))
