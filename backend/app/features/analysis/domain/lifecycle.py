"""Explicit lifecycle rules for FT-006 market analysis runs."""

from __future__ import annotations

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.domain.errors import AnalysisConflict

_ALLOWED: dict[AnalysisStatus, frozenset[AnalysisStatus]] = {
    AnalysisStatus.DRAFT: frozenset({AnalysisStatus.RUNNING}),
    AnalysisStatus.RUNNING: frozenset(
        {
            AnalysisStatus.COMPLETED,
            AnalysisStatus.COMPLETED_WITH_WARNINGS,
            AnalysisStatus.NOT_EVALUABLE,
            AnalysisStatus.FAILED,
        }
    ),
    AnalysisStatus.COMPLETED: frozenset({AnalysisStatus.SUPERSEDED}),
    AnalysisStatus.COMPLETED_WITH_WARNINGS: frozenset({AnalysisStatus.SUPERSEDED}),
    AnalysisStatus.NOT_EVALUABLE: frozenset({AnalysisStatus.SUPERSEDED}),
    AnalysisStatus.FAILED: frozenset({AnalysisStatus.SUPERSEDED}),
    AnalysisStatus.SUPERSEDED: frozenset(),
}

RETRYABLE_STATUSES = frozenset({AnalysisStatus.FAILED, AnalysisStatus.NOT_EVALUABLE})
SUPERSEDEABLE_STATUSES = frozenset(
    {
        AnalysisStatus.COMPLETED,
        AnalysisStatus.COMPLETED_WITH_WARNINGS,
        AnalysisStatus.NOT_EVALUABLE,
        AnalysisStatus.FAILED,
    }
)


def validate_transition(from_status: AnalysisStatus, to_status: AnalysisStatus) -> None:
    """Reject lifecycle changes that are not part of the documented state machine."""
    if to_status not in _ALLOWED[from_status]:
        raise AnalysisConflict(
            f"invalid analysis status transition: {from_status.value} -> {to_status.value}"
        )


def ensure_retryable(status: AnalysisStatus) -> None:
    if status not in RETRYABLE_STATUSES:
        raise AnalysisConflict(f"analysis run with status {status.value} cannot be retried")


def ensure_supersedeable(status: AnalysisStatus) -> None:
    if status not in SUPERSEDEABLE_STATUSES:
        raise AnalysisConflict(f"analysis run with status {status.value} cannot be superseded")
