"""Application service for actor-scoped UI preferences."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.user_preferences.persistence.models import UserPreferenceModel


class UserPreferenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, workspace_id: UUID, actor_id: str, kind: str
    ) -> tuple[UserPreferenceModel, ...]:
        statement = (
            select(UserPreferenceModel)
            .where(
                UserPreferenceModel.workspace_id == workspace_id,
                UserPreferenceModel.actor_id == actor_id,
                UserPreferenceModel.kind == kind,
            )
            .order_by(UserPreferenceModel.name.asc())
        )
        return tuple((await self._session.scalars(statement)).all())

    async def create(
        self,
        workspace_id: UUID,
        actor_id: str,
        kind: str,
        name: str,
        value: dict[str, object],
    ) -> UserPreferenceModel:
        now = datetime.now(UTC)
        model = UserPreferenceModel(
            id=uuid4(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            kind=kind,
            name=name.strip(),
            value=value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return model

    async def delete(
        self, workspace_id: UUID, actor_id: str, preference_id: UUID
    ) -> bool:
        statement = (
            delete(UserPreferenceModel)
            .where(
                UserPreferenceModel.id == preference_id,
                UserPreferenceModel.workspace_id == workspace_id,
                UserPreferenceModel.actor_id == actor_id,
            )
            .returning(UserPreferenceModel.id)
        )
        deleted_id = await self._session.scalar(statement)
        await self._session.commit()
        return deleted_id is not None
