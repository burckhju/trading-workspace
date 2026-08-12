import pytest

from app.features.candidate.domain.enums import CandidateStatus
from app.features.candidate.domain.lifecycle import ensure_transition


def test_candidate_lifecycle_allows_review_to_ready_for_planning() -> None:
    ensure_transition(CandidateStatus.UNDER_REVIEW, CandidateStatus.READY_FOR_PLANNING)


def test_candidate_lifecycle_rejects_identified_to_ready_for_planning() -> None:
    with pytest.raises(ValueError):
        ensure_transition(
            CandidateStatus.IDENTIFIED, CandidateStatus.READY_FOR_PLANNING
        )
