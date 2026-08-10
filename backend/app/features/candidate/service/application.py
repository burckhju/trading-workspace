"""Application service for explicit candidate creation, evaluation and lifecycle changes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.domain.enums import CandidateStatus
from app.features.candidate.domain.lifecycle import ensure_transition
from app.features.candidate.domain.qualification import evaluate_candidate
from app.features.candidate.domain.models import AnalysisReference, CandidateEvaluationInput
from app.features.candidate.persistence.models import (
    CandidateCriterionModel,
    CandidateEvaluationModel,
    CandidateEvaluationSourceModel,
    CandidateEventModel,
    CandidateModel,
)
from app.features.candidate.persistence.repositories import SqlAlchemyCandidateRepository
from app.features.candidate.service.orchestration import (
    StoredAnalysisReference,
    TopDownEvaluationOrchestrator,
)
from app.features.candidate.service.source_resolution import SemanticTopDownSourceResolver


class CandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SqlAlchemyCandidateRepository(session)

    async def create(self, workspace_id: UUID, underlying_id: UUID, actor: str) -> CandidateModel:
        if not await self._repo.underlying_exists(workspace_id, underlying_id):
            raise ValueError("underlying does not exist in workspace")
        current = await self._repo.get_by_underlying(workspace_id, underlying_id)
        if current is not None:
            return current
        now = datetime.now(UTC)
        candidate = CandidateModel(
            id=uuid4(),
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            status=CandidateStatus.IDENTIFIED.value,
            created_at=now,
            created_by=actor,
        )
        self._repo.add(candidate)
        self._repo.add(
            CandidateEventModel(
                id=uuid4(),
                candidate_id=candidate.id,
                event_type="CREATED",
                from_status=None,
                to_status=CandidateStatus.IDENTIFIED.value,
                reason=None,
                actor=actor,
                occurred_at=now,
            )
        )
        await self._repo.commit()
        return candidate

    async def list(self, workspace_id: UUID) -> tuple[CandidateModel, ...]:
        return await self._repo.list(workspace_id)

    async def get(self, workspace_id: UUID, candidate_id: UUID) -> CandidateModel:
        candidate = await self._repo.get(workspace_id, candidate_id)
        if candidate is None:
            raise ValueError("candidate not found")
        return candidate

    async def evaluate_auto(
        self,
        workspace_id: UUID,
        candidate_id: UUID,
        as_of: datetime | None = None,
    ) -> CandidateEvaluationModel:
        candidate = await self.get(workspace_id, candidate_id)
        sources = await SemanticTopDownSourceResolver(self._session).resolve(
            workspace_id=workspace_id,
            underlying_id=candidate.underlying_id,
            as_of=as_of,
        )
        return await self.evaluate_from_analyses(
            workspace_id,
            candidate_id,
            sources.market,
            sources.sector,
            sources.underlying,
        )

    async def evaluate_from_analyses(
        self,
        workspace_id: UUID,
        candidate_id: UUID,
        market: StoredAnalysisReference,
        sector: StoredAnalysisReference,
        underlying: StoredAnalysisReference,
    ) -> CandidateEvaluationModel:
        candidate = await self.get(workspace_id, candidate_id)
        resolved = await TopDownEvaluationOrchestrator(self._session).resolve(
            workspace_id=workspace_id,
            candidate_underlying_id=candidate.underlying_id,
            market=market,
            sector=sector,
            underlying=underlying,
        )
        return await self.evaluate(
            workspace_id, candidate_id, resolved.value, resolved.sources
        )

    async def evaluate(
        self,
        workspace_id: UUID,
        candidate_id: UUID,
        value: CandidateEvaluationInput,
        sources: dict[str, AnalysisReference],
    ) -> CandidateEvaluationModel:
        await self.get(workspace_id, candidate_id)
        required_roles = {"MARKET", "SECTOR", "UNDERLYING"}
        if set(sources) != required_roles:
            raise ValueError("MARKET, SECTOR and UNDERLYING provenance sources are required")
        result = evaluate_candidate(value)
        version = await self._repo.next_evaluation_version(candidate_id)
        now = datetime.now(UTC)
        model = CandidateEvaluationModel(
            id=uuid4(),
            candidate_id=candidate_id,
            version=version,
            direction=value.direction.value,
            model_id=result.model_id,
            model_version=result.model_version,
            qualification=result.qualification.value,
            quality_status=result.quality_status.value,
            warnings=list(result.warnings),
            evaluated_at=now,
        )
        self._repo.add(model)
        self._repo.add_all(
            [
                CandidateEvaluationSourceModel(
                    id=uuid4(),
                    evaluation_id=model.id,
                    role=role,
                    source_type="ANALYSIS",
                    source_id=ref.analysis_id,
                    source_version=ref.version,
                    model_id=ref.model_id,
                    model_version=ref.model_version,
                )
                for role, ref in sources.items()
            ]
        )
        self._repo.add_all(
            [
                CandidateCriterionModel(
                    id=uuid4(),
                    evaluation_id=model.id,
                    criterion_id=item.criterion_id,
                    criterion_group=item.group,
                    severity=item.severity.value,
                    evaluation=item.evaluation.value,
                    source=item.source,
                    actual_value=item.actual_value,
                    expected_value=item.expected_value,
                    numeric_value=item.numeric_value,
                    explanation=item.explanation,
                )
                for item in result.criteria
            ]
        )
        await self._repo.commit()
        return model

    async def change_status(
        self,
        workspace_id: UUID,
        candidate_id: UUID,
        target: CandidateStatus,
        actor: str,
        reason: str | None,
    ) -> CandidateModel:
        candidate = await self.get(workspace_id, candidate_id)
        current = CandidateStatus(candidate.status)
        ensure_transition(current, target)
        if target is CandidateStatus.REJECTED and not reason:
            raise ValueError("rejection reason is required")
        if current == target:
            return candidate
        candidate.status = target.value
        self._repo.add(
            CandidateEventModel(
                id=uuid4(),
                candidate_id=candidate_id,
                event_type="STATUS_CHANGED",
                from_status=current.value,
                to_status=target.value,
                reason=reason,
                actor=actor,
                occurred_at=datetime.now(UTC),
            )
        )
        await self._repo.commit()
        return candidate

    async def list_evaluations(
        self, candidate_id: UUID
    ) -> tuple[CandidateEvaluationModel, ...]:
        return await self._repo.list_evaluations(candidate_id)

    async def list_criteria(
        self, evaluation_id: UUID
    ) -> tuple[CandidateCriterionModel, ...]:
        return await self._repo.list_criteria(evaluation_id)
