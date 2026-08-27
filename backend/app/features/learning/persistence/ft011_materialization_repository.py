"""FT-012-owned persistence for FT-011 LearningEvidence materialization."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import (
    FT011Evidence,
    LearningEvidence,
    LearningEvidenceType,
)
from app.features.learning.persistence.models import (
    FT011EvidenceModel,
    LearningEvidenceModel,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection


class Ft011MaterializationRepository(Protocol):
    async def get_by_source(
        self,
        *,
        workspace_id: UUID,
        exit_review_version_id: UUID,
    ) -> LearningEvidenceProjection | None: ...

    async def get_by_evidence_id(
        self,
        *,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> LearningEvidenceProjection | None: ...

    async def add_evidence(self, evidence: LearningEvidence) -> None: ...

    async def add_source(self, source: FT011Evidence) -> None: ...


class SqlAlchemyFt011MaterializationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_source(
        self,
        *,
        workspace_id: UUID,
        exit_review_version_id: UUID,
    ) -> LearningEvidenceProjection | None:
        row = (
            await self._session.execute(
                self._base_query().where(
                    LearningEvidenceModel.workspace_id == workspace_id,
                    FT011EvidenceModel.exit_review_version_id == exit_review_version_id,
                )
            )
        ).one_or_none()
        return self._projection(row) if row is not None else None

    async def get_by_evidence_id(
        self,
        *,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> LearningEvidenceProjection | None:
        row = (
            await self._session.execute(
                self._base_query().where(
                    LearningEvidenceModel.workspace_id == workspace_id,
                    LearningEvidenceModel.id == evidence_id,
                )
            )
        ).one_or_none()
        return self._projection(row) if row is not None else None

    async def add_evidence(self, evidence: LearningEvidence) -> None:
        self._session.add(
            LearningEvidenceModel(
                id=evidence.id,
                workspace_id=evidence.workspace_id,
                evidence_type=evidence.evidence_type.value,
                created_at=evidence.created_at,
            )
        )

    async def add_source(self, source: FT011Evidence) -> None:
        self._session.add(
            FT011EvidenceModel(
                learning_evidence_id=source.learning_evidence_id,
                trade_id=source.trade_id,
                post_trade_observation_id=source.post_trade_observation_id,
                exit_review_id=source.exit_review_id,
                exit_review_version_id=source.exit_review_version_id,
            )
        )

    @staticmethod
    def _base_query():
        return (
            select(LearningEvidenceModel, FT011EvidenceModel)
            .join(
                FT011EvidenceModel,
                FT011EvidenceModel.learning_evidence_id == LearningEvidenceModel.id,
            )
            .where(
                LearningEvidenceModel.evidence_type == LearningEvidenceType.FT011.value
            )
        )

    @staticmethod
    def _projection(
        row: tuple[LearningEvidenceModel, FT011EvidenceModel],
    ) -> LearningEvidenceProjection:
        evidence_model, source_model = row
        return LearningEvidenceProjection(
            evidence=LearningEvidence(
                id=evidence_model.id,
                workspace_id=evidence_model.workspace_id,
                evidence_type=LearningEvidenceType(evidence_model.evidence_type),
                created_at=evidence_model.created_at,
            ),
            source=FT011Evidence(
                learning_evidence_id=source_model.learning_evidence_id,
                trade_id=source_model.trade_id,
                post_trade_observation_id=source_model.post_trade_observation_id,
                exit_review_id=source_model.exit_review_id,
                exit_review_version_id=source_model.exit_review_version_id,
            ),
        )
