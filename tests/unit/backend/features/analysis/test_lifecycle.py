import pytest

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.domain.errors import AnalysisConflict
from app.features.analysis.domain.lifecycle import ensure_retryable, validate_transition


def test_documented_lifecycle_transitions_are_allowed() -> None:
    validate_transition(AnalysisStatus.DRAFT, AnalysisStatus.RUNNING)
    for terminal in (
        AnalysisStatus.COMPLETED,
        AnalysisStatus.COMPLETED_WITH_WARNINGS,
        AnalysisStatus.NOT_EVALUABLE,
        AnalysisStatus.FAILED,
    ):
        validate_transition(AnalysisStatus.RUNNING, terminal)
        validate_transition(terminal, AnalysisStatus.SUPERSEDED)


def test_terminal_run_cannot_return_to_running() -> None:
    with pytest.raises(AnalysisConflict, match="invalid analysis status transition"):
        validate_transition(AnalysisStatus.COMPLETED, AnalysisStatus.RUNNING)


def test_only_failed_and_not_evaluable_runs_are_retryable() -> None:
    ensure_retryable(AnalysisStatus.FAILED)
    ensure_retryable(AnalysisStatus.NOT_EVALUABLE)
    with pytest.raises(AnalysisConflict, match="cannot be retried"):
        ensure_retryable(AnalysisStatus.COMPLETED)
