"""Explicit runtime activation service for approved FT-013 model versions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.domain.enums import ModelVersionStatus
from app.features.model.persistence.models import GovernedModelRecord, ModelVersionRecord
from app.features.model.persistence.runtime_activation_models import ModelRuntimeActivationRecord
from app.shared.utils.datetime import utc_now


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeModel:
    """Stable runtime view exposed to downstream model consumers."""

    model_id: UUID
    model_key: str
    model_version_id: UUID
    model_version: int
    definition: dict[str, object]
    activation_id: UUID
    activated_at: datetime
    activated_by: UUID
    correlation_id: str | None


class RuntimeActivationService:
    """Activate one APPROVED model version and read the current runtime selection."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(
        self, *, workspace_id: UUID, model_id: UUID
    ) -> tuple[ModelRuntimeActivationRecord, ModelVersionRecord] | None:
        model = await self._require_model(workspace_id, model_id)
        return await self._get_current_for_model(workspace_id=workspace_id, model=model)

    async def resolve_by_key(
        self, *, workspace_id: UUID, model_key: str
    ) -> ResolvedRuntimeModel | None:
        """Resolve the active APPROVED version for a stable workspace model key."""

        if not model_key.strip():
            raise ValueError("model_key is required")
        model = await self._session.scalar(
            select(GovernedModelRecord).where(
                GovernedModelRecord.workspace_id == workspace_id,
                GovernedModelRecord.model_key == model_key,
            )
        )
        if model is None:
            raise ValueError("governed model not found")

        current = await self._get_current_for_model(workspace_id=workspace_id, model=model)
        if current is None:
            return None
        activation, version = current
        return ResolvedRuntimeModel(
            model_id=model.id,
            model_key=model.model_key,
            model_version_id=version.id,
            model_version=version.version,
            definition=dict(version.definition),
            activation_id=activation.id,
            activated_at=activation.activated_at,
            activated_by=activation.activated_by,
            correlation_id=activation.correlation_id,
        )

    async def activate(
        self,
        *,
        workspace_id: UUID,
        model_id: UUID,
        model_version_id: UUID,
        actor: UUID,
        correlation_id: str | None,
    ) -> tuple[ModelRuntimeActivationRecord, ModelVersionRecord]:
        await self._require_model(workspace_id, model_id)
        version = await self._require_version(model_id, model_version_id)
        if version.status != ModelVersionStatus.APPROVED.value:
            raise ValueError("only APPROVED model version can be activated")

        current = await self.get_current(workspace_id=workspace_id, model_id=model_id)
        if current is not None and current[0].model_version_id == model_version_id:
            raise ValueError("model version is already active")

        activation = ModelRuntimeActivationRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            model_id=model_id,
            model_version_id=model_version_id,
            activated_at=utc_now(),
            activated_by=actor,
            correlation_id=correlation_id,
        )
        self._session.add(activation)
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return activation, version

    async def _get_current_for_model(
        self, *, workspace_id: UUID, model: GovernedModelRecord
    ) -> tuple[ModelRuntimeActivationRecord, ModelVersionRecord] | None:
        activation = await self._session.scalar(
            select(ModelRuntimeActivationRecord)
            .where(
                ModelRuntimeActivationRecord.workspace_id == workspace_id,
                ModelRuntimeActivationRecord.model_id == model.id,
            )
            .order_by(
                ModelRuntimeActivationRecord.activated_at.desc(),
                ModelRuntimeActivationRecord.id.desc(),
            )
            .limit(1)
        )
        if activation is None:
            return None
        version = await self._require_version(model.id, activation.model_version_id)
        if version.status != ModelVersionStatus.APPROVED.value:
            raise ValueError("active model version is not APPROVED")
        return activation, version

    async def _require_model(self, workspace_id: UUID, model_id: UUID) -> GovernedModelRecord:
        model = await self._session.scalar(
            select(GovernedModelRecord).where(
                GovernedModelRecord.id == model_id,
                GovernedModelRecord.workspace_id == workspace_id,
            )
        )
        if model is None:
            raise ValueError("governed model not found")
        return model

    async def _require_version(self, model_id: UUID, version_id: UUID) -> ModelVersionRecord:
        version = await self._session.scalar(
            select(ModelVersionRecord).where(
                ModelVersionRecord.id == version_id,
                ModelVersionRecord.model_id == model_id,
            )
        )
        if version is None:
            raise ValueError("model version not found")
        return version
