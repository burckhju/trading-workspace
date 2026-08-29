"""Explicit runtime activation service for approved FT-013 model versions."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.domain.enums import ModelVersionStatus
from app.features.model.persistence.models import GovernedModelRecord, ModelVersionRecord
from app.features.model.persistence.runtime_activation_models import ModelRuntimeActivationRecord
from app.shared.utils.datetime import utc_now


class RuntimeActivationService:
    """Activate one APPROVED model version and read the current runtime selection."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(
        self, *, workspace_id: UUID, model_id: UUID
    ) -> tuple[ModelRuntimeActivationRecord, ModelVersionRecord] | None:
        await self._require_model(workspace_id, model_id)
        activation = await self._session.scalar(
            select(ModelRuntimeActivationRecord)
            .where(
                ModelRuntimeActivationRecord.workspace_id == workspace_id,
                ModelRuntimeActivationRecord.model_id == model_id,
            )
            .order_by(
                ModelRuntimeActivationRecord.activated_at.desc(),
                ModelRuntimeActivationRecord.id.desc(),
            )
            .limit(1)
        )
        if activation is None:
            return None
        version = await self._require_version(model_id, activation.model_version_id)
        return activation, version

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
