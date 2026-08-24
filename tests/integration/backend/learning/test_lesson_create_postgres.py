from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from test_trade_link_application_postgres import (
    _seed_observation,
    _seed_parents,
)

from app.features.learning.application.lesson_service import (
    LessonEvidenceInput,
    LessonService,
)
from app.features.learning.domain import LessonEvidenceRelation
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
async def test_create_lesson_v1_with_supporting_evidence(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    _, observation_version_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )

    evidence_id = uuid4()
    await learning_session.execute(
        text("""
            insert into learning_evidence (
                id, workspace_id, evidence_type, created_at
            )
            values (
                :id,
                :workspace_id,
                'EXTERNAL_OBSERVATION',
                :created_at
            )
            """),
        {
            "id": evidence_id,
            "workspace_id": workspace_id,
            "created_at": NOW,
        },
    )

    await learning_session.execute(
        text("""
            insert into external_observation_evidence (
                learning_evidence_id,
                external_observation_version_id
            )
            values (:evidence_id, :source_id)
            """),
        {
            "evidence_id": evidence_id,
            "source_id": observation_version_id,
        },
    )

    uow = cast(
        LearningTradeLinkUnitOfWork,
        SqlAlchemyLearningTradeLinkUnitOfWork(learning_session),
    )
    result = await LessonService(
        uow=uow,
        clock=Clock(),
        id_factory=Ids(),
    ).create(
        workspace_id=workspace_id,
        title="Follow the process",
        main_category="PROCESS",
        content="Wait for confirmation before entry.",
        evidence=(
            LessonEvidenceInput(
                learning_evidence_id=evidence_id,
                relation=LessonEvidenceRelation.SUPPORTS,
            ),
        ),
        actor_id=uuid4(),
    )

    lesson = (
        await learning_session.execute(
            text("""
                select current_version_id, current_state
                from lessons
                where id = :id
                """),
            {"id": result.lesson.id},
        )
    ).one()
    version = (
        await learning_session.execute(
            text("""
                select version, supersedes_version_id
                from lesson_versions
                where id = :id
                """),
            {"id": result.version.id},
        )
    ).one()
    link_count = await learning_session.scalar(
        text("""
            select count(*)
            from lesson_evidence_links
            where lesson_version_id = :version_id
              and relation = 'SUPPORTS'
            """),
        {"version_id": result.version.id},
    )

    assert lesson.current_version_id == result.version.id
    assert lesson.current_state == "CURRENT"
    assert version.version == 1
    assert version.supersedes_version_id is None
    assert link_count == 1
