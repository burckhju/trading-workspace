"""Candidate lifecycle invariants; user decisions remain explicit."""

from app.features.candidate.domain.enums import CandidateStatus

_ALLOWED: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.IDENTIFIED: frozenset(
        {CandidateStatus.UNDER_REVIEW, CandidateStatus.WATCHING, CandidateStatus.REJECTED}
    ),
    CandidateStatus.UNDER_REVIEW: frozenset(
        {
            CandidateStatus.WATCHING,
            CandidateStatus.READY_FOR_PLANNING,
            CandidateStatus.REJECTED,
        }
    ),
    CandidateStatus.WATCHING: frozenset(
        {
            CandidateStatus.UNDER_REVIEW,
            CandidateStatus.READY_FOR_PLANNING,
            CandidateStatus.REJECTED,
        }
    ),
    CandidateStatus.READY_FOR_PLANNING: frozenset(
        {CandidateStatus.WATCHING, CandidateStatus.REJECTED}
    ),
    CandidateStatus.REJECTED: frozenset({CandidateStatus.WATCHING, CandidateStatus.UNDER_REVIEW}),
}


def ensure_transition(current: CandidateStatus, target: CandidateStatus) -> None:
    if current == target:
        return
    if target not in _ALLOWED[current]:
        raise ValueError(f"invalid candidate transition: {current.value} -> {target.value}")
