from datetime import UTC, datetime
from uuid import uuid4

from app.features.learning.domain import Lesson, LessonState
from app.features.learning.persistence.mapping import lesson_from_model, lesson_to_model

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def test_lesson_mapping_roundtrip() -> None:
    value = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Keep process discipline",
        current_version_id=uuid4(),
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=uuid4(),
        updated_at=NOW,
        updated_by=uuid4(),
    )
    assert lesson_from_model(lesson_to_model(value)) == value
