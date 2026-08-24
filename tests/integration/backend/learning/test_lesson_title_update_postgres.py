from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from test_trade_link_application_postgres import _seed_parents

from app.features.learning.application.lesson_service import LessonService
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


@pytest.mark.asyncio
async def test_title_update_keeps_current_version(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, _, _ = await _seed_parents(learning_session)

    lesson_id = uuid4()
    version_id = uuid4()
    actor_id = uuid4()

    # Lesson <-> current LessonVersion is a deferred FK cycle.
    # Seed both rows with their final identities inside the same transaction.
    await learning_session.execute(
        text(
            """
            set constraints all deferred
            """
        )
    )

    await learning_session.execute(
        text(
            """
            insert into lessons (
                id, workspace_id, title,
                current_version_id, current_state,
                created_at, created_by, updated_at, updated_by
            )
            values (
                :id, :workspace_id, 'Old title',
                :version_id, 'CURRENT',
                :now, :actor_id, :now, :actor_id
            )
            """
        ),
        {
            "id": lesson_id,
            "workspace_id": workspace_id,
            "version_id": version_id,
            "now": NOW,
            "actor_id": actor_id,
        },
    )

    await learning_session.execute(
        text(
            """
            insert into lesson_versions (
                id, lesson_id, version,
                main_category, content,
                created_at, created_by,
                supersedes_version_id
            )
            values (
                :id, :lesson_id, 1,
                'PROCESS', 'content',
                :now, :actor_id,
                null
            )
            """
        ),
        {
            "id": version_id,
            "lesson_id": lesson_id,
            "now": NOW,
            "actor_id": actor_id,
        },
    )

    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(learning_session),
    )
    await LessonService(
        uow=uow,
        clock=Clock(),
        id_factory=Ids(),
    ).update_title(
        workspace_id=workspace_id,
        lesson_id=lesson_id,
        title="New title",
        actor_id=actor_id,
    )

    row = (
        await learning_session.execute(
            text(
                """
                select title, current_version_id
                from lessons
                where id = :lesson_id
                """
            ),
            {"lesson_id": lesson_id},
        )
    ).one()

    version_count = await learning_session.scalar(
        text(
            """
            select count(*)
            from lesson_versions
            where lesson_id = :lesson_id
            """
        ),
        {"lesson_id": lesson_id},
    )

    assert row.title == "New title"
    assert row.current_version_id == version_id
    assert version_count == 1
