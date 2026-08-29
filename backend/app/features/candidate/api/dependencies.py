"""Request-scoped candidate service dependency."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.candidate.service.application import CandidateService
from app.features.candidate.service.runtime_readiness import (
    RuntimeAwareCandidateLiveWorkflowService,
)


async def get_candidate_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[CandidateService]:
    yield CandidateService(session)


async def get_candidate_live_workflow_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[RuntimeAwareCandidateLiveWorkflowService]:
    yield RuntimeAwareCandidateLiveWorkflowService(session)
