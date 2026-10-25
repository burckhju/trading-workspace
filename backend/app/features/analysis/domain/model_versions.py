"""Exact FT-006 calculation dispatch; no implicit latest version or activation.

Callers persist and hash the exact model ID/version. Historical run, retry and
verification use the same registry; unknown identities never select a fallback.
"""

from __future__ import annotations

from app.features.analysis.domain import calculator, calculator_v1_0_1
from app.features.analysis.domain.errors import AnalysisConflict
from app.features.analysis.domain.models import AnalysisComputation, AnalysisParameters, SnapshotRow


def model_is_available(*, model_id: str, model_version: str) -> bool:
    return model_id == calculator.MODEL_ID and model_version in (
        calculator.MODEL_VERSION,
        calculator_v1_0_1.MODEL_VERSION,
    )


def require_model(*, model_id: str, model_version: str) -> None:
    """Validate an execution identity before creating any run or snapshot."""
    if not model_is_available(model_id=model_id, model_version=model_version):
        raise AnalysisConflict(f"analysis model {model_id} {model_version} is not available")


def calculate_for_version(
    parameters: AnalysisParameters,
    rows: tuple[SnapshotRow, ...],
    *,
    model_id: str,
    model_version: str,
) -> AnalysisComputation:
    """Reject unknown identities rather than falling back to another policy."""
    require_model(model_id=model_id, model_version=model_version)
    if model_version == calculator.MODEL_VERSION:
        return calculator.calculate(parameters, rows)
    return calculator_v1_0_1.calculate(parameters, rows)
