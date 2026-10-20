"""Public create transaction; composable low-level lesson operations stay unchanged."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.learning.application.lesson_service import (
    CreateLessonResult,
    LessonErrorCode,
    LessonEvidenceInput,
    LessonService,
    LessonServiceError,
)
from app.features.learning.domain import LessonEvidenceRelation


class Uow:
    def __init__(self):
        self.steps = []
        self.fail_commit = False

    async def __aenter__(self):
        self.steps.append("enter")
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type:
            self.steps.append("rollback")

    async def commit(self):
        self.steps.append("commit")
        if self.fail_commit:
            raise RuntimeError("commit failed")


@pytest.fixture
def command():
    uow = Uow()
    service = LessonService(uow=uow, clock=None, id_factory=None)
    created = CreateLessonResult(SimpleNamespace(id=uuid4()), None, ())
    tags = (object(),)

    async def create(**kwargs):
        uow.steps.append("create")
        return created

    async def replace_tags(**kwargs):
        uow.steps.append("tags")
        return tags

    service.create = AsyncMock(side_effect=create)
    service.replace_tags = AsyncMock(side_effect=replace_tags)
    args = dict(
        workspace_id=uuid4(),
        title="Explicit title",
        main_category="Process",
        content="User interpretation, not a generated model change.",
        evidence=(LessonEvidenceInput(uuid4(), LessonEvidenceRelation.SUPPORTS),),
        tags=("Process",),
        actor_id=uuid4(),
    )
    return service, uow, args, created, tags


async def test_commit_only_after_complete_create_and_tags(command):
    service, uow, args, created, tags = command
    result = await service.create_with_tags(**args)
    assert result.created is created and result.tags == tags
    assert uow.steps == ["enter", "create", "tags", "commit"]
    service.create.assert_awaited_once_with(**{k: v for k, v in args.items() if k != "tags"})
    service.replace_tags.assert_awaited_once_with(
        workspace_id=args["workspace_id"],
        lesson_id=created.lesson.id,
        tags=args["tags"],
        actor_id=args["actor_id"],
    )


async def test_invalid_tags_roll_back_without_premature_commit(command):
    service, uow, args, _, _ = command
    error = LessonServiceError(LessonErrorCode.LESSON_INVALID, "blank tag")
    service.replace_tags.side_effect = error
    with pytest.raises(LessonServiceError) as rejected:
        await service.create_with_tags(**args)
    assert rejected.value is error
    assert uow.steps == ["enter", "create", "rollback"]


async def test_commit_failure_is_not_reported_as_success(command):
    service, uow, args, _, _ = command
    uow.fail_commit = True
    with pytest.raises(RuntimeError, match="commit failed"):
        await service.create_with_tags(**args)
    assert uow.steps == ["enter", "create", "tags", "commit", "rollback"]


async def test_creation_failure_never_assigns_tags(command):
    service, uow, args, _, _ = command
    service.create.side_effect = LessonServiceError(
        LessonErrorCode.LESSON_EVIDENCE_REQUIRED, "missing evidence"
    )
    with pytest.raises(LessonServiceError):
        await service.create_with_tags(**args)
    service.replace_tags.assert_not_awaited()
    assert uow.steps == ["enter", "rollback"]
