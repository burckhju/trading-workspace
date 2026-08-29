"""Runtime-aware Candidate live-readiness built on the FT-013/015 contracts."""

from dataclasses import replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.domain.runtime_definition import adapt_candidate_runtime_definition
from app.features.candidate.service.live_workflow import (
    CandidateLiveWorkflow,
    CandidateLiveWorkflowService,
    WorkflowStep,
)
from app.features.model.service.runtime_activation_service import (
    ResolvedRuntimeModel,
    RuntimeActivationService,
)

CANDIDATE_MODEL_KEY = "TOP_DOWN_CANDIDATE"


class RuntimeAwareCandidateLiveWorkflowService(CandidateLiveWorkflowService):
    """Add active/executable governed Candidate-model readiness to the live workflow."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._runtime = RuntimeActivationService(session)

    async def inspect(
        self,
        *,
        workspace_id: UUID,
        candidate_id: UUID,
        as_of=None,
    ) -> CandidateLiveWorkflow:
        workflow = await super().inspect(
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            as_of=as_of,
        )
        step = await self._runtime_step(workspace_id)
        runtime_ready = step.status == "COMPLETE"
        next_action = workflow.next_action or (step.action if step.status == "BLOCKED" else None)
        return replace(
            workflow,
            ready=workflow.ready and runtime_ready,
            can_evaluate=workflow.can_evaluate and runtime_ready,
            next_action=next_action,
            steps=(*workflow.steps, step),
        )

    async def _runtime_step(self, workspace_id: UUID) -> WorkflowStep:
        try:
            runtime = await self._resolve_runtime(workspace_id)
        except ValueError as exc:
            return WorkflowStep(
                code="CANDIDATE_RUNTIME_MODEL",
                label="Candidate runtime model",
                status="BLOCKED",
                detail=f"Active Candidate model is not executable: {exc}",
                action="ACTIVATE_COMPATIBLE_CANDIDATE_MODEL",
            )
        if runtime is None:
            return WorkflowStep(
                code="CANDIDATE_RUNTIME_MODEL",
                label="Candidate runtime model",
                status="BLOCKED",
                detail="No active TOP_DOWN_CANDIDATE model version is available.",
                action="ACTIVATE_CANDIDATE_MODEL",
            )

        try:
            adapt_candidate_runtime_definition(
                model_key=runtime.model_key,
                version=runtime.model_version,
                definition=runtime.definition,
            )
        except ValueError as exc:
            return WorkflowStep(
                code="CANDIDATE_RUNTIME_MODEL",
                label="Candidate runtime model",
                status="BLOCKED",
                detail=f"Active Candidate model is not executable: {exc}",
                action="ACTIVATE_COMPATIBLE_CANDIDATE_MODEL",
                resource_id=runtime.model_version_id,
            )

        return WorkflowStep(
            code="CANDIDATE_RUNTIME_MODEL",
            label="Candidate runtime model",
            status="COMPLETE",
            detail=(
                f"Active executable model {runtime.model_key} "
                f"version {runtime.model_version}."
            ),
            resource_id=runtime.model_version_id,
        )

    async def _resolve_runtime(self, workspace_id: UUID) -> ResolvedRuntimeModel | None:
        return await self._runtime.resolve_by_key(
            workspace_id=workspace_id,
            model_key=CANDIDATE_MODEL_KEY,
        )
