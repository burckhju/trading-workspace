"""Exact FT-006 calculation dispatch; no implicit latest version or activation.

Callers must persist and hash the exact model ID/version they explicitly pass.
The existing application continues to use its released 1.0.0 entry point until
its run/retry/verification/provenance contracts are integrated and qualified.
"""

from __future__ import annotations

from app.features.analysis.domain import calculator, calculator_v1_0_1
from app.features.analysis.domain.errors import AnalysisConflict
from app.features.analysis.domain.models import AnalysisComputation, AnalysisParameters, SnapshotRow


def calculate_for_version(
    parameters: AnalysisParameters,
    rows: tuple[SnapshotRow, ...],
    *,
    model_id: str,
    model_version: str,
) -> AnalysisComputation:
    """Reject unknown identities rather than falling back to another policy."""
    if model_id != calculator.MODEL_ID:
        raise AnalysisConflict(f"analysis model {model_id} {model_version} is not available")
    if model_version == calculator.MODEL_VERSION:
        return calculator.calculate(parameters, rows)
    if model_version == calculator_v1_0_1.MODEL_VERSION:
        return calculator_v1_0_1.calculate(parameters, rows)
    raise AnalysisConflict(f"analysis model {model_id} {model_version} is not available")
