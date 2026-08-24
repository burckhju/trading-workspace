from app.features.learning.domain import LessonEvidenceRelation, LessonState


def test_lesson_state_contract_is_exact() -> None:
    assert {value.value for value in LessonState} == {
        "CURRENT",
        "REVIEW_RECOMMENDED",
        "RETIRED",
    }


def test_lesson_evidence_relation_contract_is_exact() -> None:
    assert {value.value for value in LessonEvidenceRelation} == {
        "SUPPORTS",
        "CONTRADICTS",
        "CONTEXTUAL",
    }
