"""Application service for FT-013 controlled model governance."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.models import (
    LearningEvidenceModel,
    LessonVersionModel,
)
from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ProposalStatus,
    ValidationConclusion,
    ValidationMethod,
)
from app.features.model.domain.models import (
    GovernedModel,
    Hypothesis,
    ModelApproval,
    ModelChangeProposal,
    ModelValidation,
    ModelVersion,
)
from app.features.model.persistence.models import (
    GovernedModelRecord,
    HypothesisEvidenceRecord,
    HypothesisRecord,
    ModelApprovalRecord,
    ModelChangeProposalRecord,
    ModelValidationEvidenceRecord,
    ModelValidationRecord,
    ModelVersionRecord,
)
from app.shared.utils.datetime import utc_now


class ModelGovernanceService:
    """Coordinate explicit, non-activating model-governance transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_model(
        self,
        *,
        workspace_id: UUID,
        model_key: str,
        name: str,
        purpose: str,
        initial_definition: dict[str, object],
        actor: UUID,
    ) -> tuple[GovernedModel, ModelVersion]:
        now = utc_now()
        model = GovernedModel(
            id=uuid4(),
            workspace_id=workspace_id,
            model_key=model_key,
            name=name,
            purpose=purpose,
            created_at=now,
            created_by=actor,
        )
        version = ModelVersion(
            id=uuid4(),
            model_id=model.id,
            version=1,
            status=ModelVersionStatus.DRAFT,
            definition=initial_definition,
            change_summary="Initial governed version",
            created_at=now,
            created_by=actor,
        )
        self._session.add(
            GovernedModelRecord(
                id=model.id,
                workspace_id=model.workspace_id,
                model_key=model.model_key,
                name=model.name,
                purpose=model.purpose,
                created_at=model.created_at,
                created_by=model.created_by,
            )
        )
        self._session.add(self._version_record(version))
        await self._commit()
        return model, version

    async def approve_initial_version(
        self,
        *,
        workspace_id: UUID,
        model_id: UUID,
        version_id: UUID,
        actor: UUID,
        correlation_id: str | None,
    ) -> ModelApproval:
        model = await self._require_model(workspace_id, model_id)
        version = await self._require_version(model.id, version_id)
        if version.version != 1 or version.status != ModelVersionStatus.DRAFT.value:
            raise ValueError("only initial DRAFT model version can be directly approved")
        existing = await self._session.scalar(
            select(ModelApprovalRecord).where(ModelApprovalRecord.model_version_id == version_id)
        )
        if existing is not None:
            raise ValueError("model version is already approved")
        version.status = ModelVersionStatus.APPROVED.value
        approval = ModelApproval(
            id=uuid4(),
            proposal_id=None,
            model_version_id=version_id,
            approved_at=utc_now(),
            approved_by=actor,
            correlation_id=correlation_id,
        )
        self._session.add(
            ModelApprovalRecord(
                id=approval.id,
                proposal_id=None,
                model_version_id=approval.model_version_id,
                approved_at=approval.approved_at,
                approved_by=approval.approved_by,
                correlation_id=approval.correlation_id,
            )
        )
        await self._commit()
        return approval

    async def create_hypothesis(
        self,
        *,
        workspace_id: UUID,
        title: str,
        statement: str,
        evidence_ids: tuple[UUID, ...],
        source_lesson_version_id: UUID | None,
        actor: UUID,
    ) -> Hypothesis:
        if not evidence_ids and source_lesson_version_id is None:
            raise ValueError("hypothesis requires evidence or a lesson version")
        if source_lesson_version_id is not None:
            lesson_exists = await self._session.scalar(
                select(LessonVersionModel.id).where(
                    LessonVersionModel.id == source_lesson_version_id
                )
            )
            if lesson_exists is None:
                raise ValueError("source lesson version not found")
        await self._require_evidence(workspace_id, evidence_ids)
        hypothesis = Hypothesis(
            id=uuid4(),
            workspace_id=workspace_id,
            title=title,
            statement=statement,
            status=HypothesisStatus.OPEN,
            source_lesson_version_id=source_lesson_version_id,
            created_at=utc_now(),
            created_by=actor,
        )
        self._session.add(
            HypothesisRecord(
                id=hypothesis.id,
                workspace_id=hypothesis.workspace_id,
                title=hypothesis.title,
                statement=hypothesis.statement,
                status=hypothesis.status.value,
                source_lesson_version_id=hypothesis.source_lesson_version_id,
                created_at=hypothesis.created_at,
                created_by=hypothesis.created_by,
            )
        )
        await self._session.flush()
        for evidence_id in dict.fromkeys(evidence_ids):
            self._session.add(
                HypothesisEvidenceRecord(
                    hypothesis_id=hypothesis.id,
                    learning_evidence_id=evidence_id,
                )
            )
        await self._commit()
        return hypothesis

    async def create_proposal(
        self,
        *,
        workspace_id: UUID,
        model_id: UUID,
        base_model_version_id: UUID,
        hypothesis_id: UUID,
        proposed_definition: dict[str, object],
        rationale: str,
        actor: UUID,
    ) -> ModelChangeProposal:
        model = await self._require_model(workspace_id, model_id)
        base = await self._require_version(model.id, base_model_version_id)
        if base.status != ModelVersionStatus.APPROVED.value:
            raise ValueError("proposal base version must be APPROVED")
        hypothesis = await self._session.scalar(
            select(HypothesisRecord).where(
                HypothesisRecord.id == hypothesis_id,
                HypothesisRecord.workspace_id == workspace_id,
            )
        )
        if hypothesis is None:
            raise ValueError("hypothesis not found")
        if hypothesis.status == HypothesisStatus.CLOSED.value:
            raise ValueError("closed hypothesis cannot create proposal")
        proposal = ModelChangeProposal(
            id=uuid4(),
            workspace_id=workspace_id,
            model_id=model_id,
            base_model_version_id=base_model_version_id,
            hypothesis_id=hypothesis_id,
            status=ProposalStatus.DRAFT,
            proposed_definition=proposed_definition,
            rationale=rationale,
            created_at=utc_now(),
            created_by=actor,
        )
        self._session.add(
            ModelChangeProposalRecord(
                id=proposal.id,
                workspace_id=proposal.workspace_id,
                model_id=proposal.model_id,
                base_model_version_id=proposal.base_model_version_id,
                hypothesis_id=proposal.hypothesis_id,
                status=proposal.status.value,
                proposed_definition=proposal.proposed_definition,
                rationale=proposal.rationale,
                created_at=proposal.created_at,
                created_by=proposal.created_by,
            )
        )
        hypothesis.status = HypothesisStatus.PROPOSED.value
        await self._commit()
        return proposal

    async def validate_proposal(
        self,
        *,
        workspace_id: UUID,
        proposal_id: UUID,
        evidence_ids: tuple[UUID, ...],
        evidence_cutoff_at: datetime,
        conclusion: ValidationConclusion,
        metrics: dict[str, object],
        notes: str | None,
        actor: UUID,
    ) -> ModelValidation:
        proposal = await self._require_proposal(workspace_id, proposal_id)
        if proposal.status == ProposalStatus.APPROVED.value:
            raise ValueError("approved proposal cannot be revalidated")
        evidence = await self._require_evidence(workspace_id, evidence_ids)
        if not evidence:
            raise ValueError("retrospective validation requires evidence")
        if any(item.created_at > evidence_cutoff_at for item in evidence):
            raise ValueError("validation evidence violates evidence cutoff")
        validation = ModelValidation(
            id=uuid4(),
            proposal_id=proposal_id,
            method=ValidationMethod.RETROSPECTIVE,
            evidence_cutoff_at=evidence_cutoff_at,
            conclusion=conclusion,
            metrics=metrics,
            notes=notes,
            created_at=utc_now(),
            created_by=actor,
        )
        self._session.add(
            ModelValidationRecord(
                id=validation.id,
                proposal_id=validation.proposal_id,
                method=validation.method.value,
                evidence_cutoff_at=validation.evidence_cutoff_at,
                conclusion=validation.conclusion.value,
                metrics=validation.metrics,
                notes=validation.notes,
                created_at=validation.created_at,
                created_by=validation.created_by,
            )
        )
        await self._session.flush()
        for evidence_id in dict.fromkeys(evidence_ids):
            self._session.add(
                ModelValidationEvidenceRecord(
                    validation_id=validation.id,
                    learning_evidence_id=evidence_id,
                )
            )
        proposal.status = ProposalStatus.VALIDATED.value
        await self._commit()
        return validation

    async def approve_proposal(
        self,
        *,
        workspace_id: UUID,
        proposal_id: UUID,
        actor: UUID,
        correlation_id: str | None,
    ) -> tuple[ModelVersion, ModelApproval]:
        proposal = await self._require_proposal(workspace_id, proposal_id)
        if proposal.status != ProposalStatus.VALIDATED.value:
            raise ValueError("only VALIDATED proposal can be approved")
        latest_validation = await self._session.scalar(
            select(ModelValidationRecord)
            .where(ModelValidationRecord.proposal_id == proposal_id)
            .order_by(ModelValidationRecord.created_at.desc())
            .limit(1)
        )
        if latest_validation is None:
            raise ValueError("proposal requires validation before approval")
        latest_version = await self._session.scalar(
            select(ModelVersionRecord)
            .where(ModelVersionRecord.model_id == proposal.model_id)
            .order_by(ModelVersionRecord.version.desc())
            .limit(1)
        )
        if latest_version is None:
            raise ValueError("model has no versions")
        if latest_version.id != proposal.base_model_version_id:
            raise ValueError("proposal base version is stale; rebase before approval")
        now = utc_now()
        version = ModelVersion(
            id=uuid4(),
            model_id=proposal.model_id,
            version=latest_version.version + 1,
            status=ModelVersionStatus.APPROVED,
            definition=proposal.proposed_definition,
            change_summary=proposal.rationale,
            created_at=now,
            created_by=actor,
            previous_version_id=latest_version.id,
        )
        self._session.add(self._version_record(version))
        approval = ModelApproval(
            id=uuid4(),
            proposal_id=proposal_id,
            model_version_id=version.id,
            approved_at=now,
            approved_by=actor,
            correlation_id=correlation_id,
        )
        self._session.add(
            ModelApprovalRecord(
                id=approval.id,
                proposal_id=proposal_id,
                model_version_id=version.id,
                approved_at=now,
                approved_by=actor,
                correlation_id=correlation_id,
            )
        )
        proposal.status = ProposalStatus.APPROVED.value
        hypothesis = await self._session.get(HypothesisRecord, proposal.hypothesis_id)
        if hypothesis is not None:
            hypothesis.status = HypothesisStatus.CLOSED.value
        await self._commit()
        return version, approval

    async def list_models(self, workspace_id: UUID) -> list[GovernedModelRecord]:
        result = await self._session.scalars(
            select(GovernedModelRecord)
            .where(GovernedModelRecord.workspace_id == workspace_id)
            .order_by(GovernedModelRecord.model_key)
        )
        return list(result)

    async def list_versions(self, workspace_id: UUID, model_id: UUID) -> list[ModelVersionRecord]:
        await self._require_model(workspace_id, model_id)
        result = await self._session.scalars(
            select(ModelVersionRecord)
            .where(ModelVersionRecord.model_id == model_id)
            .order_by(ModelVersionRecord.version)
        )
        return list(result)

    async def get_proposal(
        self, workspace_id: UUID, proposal_id: UUID
    ) -> ModelChangeProposalRecord:
        return await self._require_proposal(workspace_id, proposal_id)

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

    async def _require_proposal(
        self, workspace_id: UUID, proposal_id: UUID
    ) -> ModelChangeProposalRecord:
        proposal = await self._session.scalar(
            select(ModelChangeProposalRecord).where(
                ModelChangeProposalRecord.id == proposal_id,
                ModelChangeProposalRecord.workspace_id == workspace_id,
            )
        )
        if proposal is None:
            raise ValueError("model change proposal not found")
        return proposal

    async def _require_evidence(
        self, workspace_id: UUID, evidence_ids: tuple[UUID, ...]
    ) -> list[LearningEvidenceModel]:
        unique = tuple(dict.fromkeys(evidence_ids))
        if not unique:
            return []
        result = await self._session.scalars(
            select(LearningEvidenceModel).where(
                LearningEvidenceModel.workspace_id == workspace_id,
                LearningEvidenceModel.id.in_(unique),
            )
        )
        found = list(result)
        if len(found) != len(unique):
            raise ValueError("one or more learning evidence anchors were not found")
        return found

    @staticmethod
    def _version_record(version: ModelVersion) -> ModelVersionRecord:
        return ModelVersionRecord(
            id=version.id,
            model_id=version.model_id,
            version=version.version,
            status=version.status.value,
            definition=version.definition,
            change_summary=version.change_summary,
            created_at=version.created_at,
            created_by=version.created_by,
            previous_version_id=version.previous_version_id,
        )

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
