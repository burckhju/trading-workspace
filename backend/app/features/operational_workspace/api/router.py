"""Read-only operational workspace endpoints."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.operational_workspace.api.dtos import (
    OperationalActionResponse,
    OperationalWorkspaceResponse,
)
from app.features.operational_workspace.service import OperationalWorkspaceReadModel

router = APIRouter(prefix="/api/v1/operational-workspace", tags=["operational-workspace"])

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.get("/actions", response_model=OperationalWorkspaceResponse)
async def list_operational_actions(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OperationalWorkspaceResponse:
    actions = await OperationalWorkspaceReadModel(session).list_actions(workspace_id=WORKSPACE_ID)
    return OperationalWorkspaceResponse(
        generated_at=datetime.now(UTC),
        actions=[OperationalActionResponse(**asdict(action)) for action in actions],
    )
