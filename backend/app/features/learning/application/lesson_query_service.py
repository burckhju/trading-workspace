"""Lesson read projections for FT-012."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.features.learning.domain import Lesson, LessonEvidenceLink, LessonVersion
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


@dataclass(frozen=True, slots=True)
class LessonProjection:
    lesson: Lesson
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


@dataclass(frozen=True, slots=True)
class LessonVersionProjection:
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


class LessonPageErrorCode(StrEnum):
    INVALID_PAGE_REQUEST = "INVALID_PAGE_REQUEST"
    INVALID_CURSOR = "INVALID_CURSOR"


class LessonPageError(Exception):
    def __init__(self, code: LessonPageErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LessonPage:
    items: tuple[LessonProjection, ...]
    next_cursor: str | None


def _encode_cursor(*, updated_at: datetime, lesson_id: UUID) -> str:
    payload = {
        "v": 1,
        "updated_at": updated_at.isoformat(),
        "lesson_id": str(lesson_id),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    if not cursor or len(cursor) > 1024:
        raise LessonPageError(
            LessonPageErrorCode.INVALID_CURSOR,
            "invalid lesson cursor",
        )

    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("v") != 1
            or not isinstance(payload.get("updated_at"), str)
            or not isinstance(payload.get("lesson_id"), str)
        ):
            raise ValueError("invalid cursor payload")

        updated_at = datetime.fromisoformat(payload["updated_at"])
        lesson_id = UUID(payload["lesson_id"])
        if updated_at.tzinfo is None:
            raise ValueError("cursor datetime must be timezone-aware")
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise LessonPageError(
            LessonPageErrorCode.INVALID_CURSOR,
            "invalid lesson cursor",
        ) from exc

    return updated_at, lesson_id


class LessonQueryService:
    def __init__(self, *, uow: LearningTradeLinkUnitOfWork) -> None:
        self._uow = uow

    async def get(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> LessonProjection | None:
        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            return None
        version = await self._uow.lesson_versions.get(lesson.current_version_id)
        if version is None:
            raise RuntimeError("current LessonVersion missing")
        links = await self._uow.lesson_evidence_links.list_for_version(version.id)
        return LessonProjection(
            lesson=lesson,
            version=version,
            evidence_links=tuple(links),
        )

    async def history(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> tuple[LessonVersionProjection, ...] | None:
        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            return None

        versions = await self._uow.lesson_versions.list_for_lesson(lesson.id)
        result: list[LessonVersionProjection] = []
        for version in versions:
            links = await self._uow.lesson_evidence_links.list_for_version(version.id)
            result.append(
                LessonVersionProjection(
                    version=version,
                    evidence_links=tuple(links),
                )
            )
        return tuple(result)

    async def page(
        self,
        *,
        workspace_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> LessonPage:
        if limit < 1 or limit > 200:
            raise LessonPageError(
                LessonPageErrorCode.INVALID_PAGE_REQUEST,
                "limit must be between 1 and 200",
            )

        lessons = tuple(await self._uow.lessons.list_for_workspace(workspace_id))

        if cursor is not None:
            cursor_updated_at, cursor_id = _decode_cursor(cursor)
            lessons = tuple(
                lesson
                for lesson in lessons
                if (
                    lesson.updated_at < cursor_updated_at
                    or (lesson.updated_at == cursor_updated_at and lesson.id > cursor_id)
                )
            )

        selected = lessons[: limit + 1]
        has_more = len(selected) > limit
        page_lessons = selected[:limit]

        result: list[LessonProjection] = []
        for lesson in page_lessons:
            version = await self._uow.lesson_versions.get(lesson.current_version_id)
            if version is None:
                raise RuntimeError("current LessonVersion missing")

            links = await self._uow.lesson_evidence_links.list_for_version(version.id)
            result.append(
                LessonProjection(
                    lesson=lesson,
                    version=version,
                    evidence_links=tuple(links),
                )
            )

        next_cursor = None
        if has_more and page_lessons:
            last = page_lessons[-1]
            next_cursor = _encode_cursor(
                updated_at=last.updated_at,
                lesson_id=last.id,
            )

        return LessonPage(
            items=tuple(result),
            next_cursor=next_cursor,
        )
