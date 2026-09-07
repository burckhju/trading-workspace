"""Read-only operational workspace endpoints."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import ApplicationContainer, get_container
from app.database.dependencies import get_database_session
from app.features.operational_workspace.api.dtos import (
    OperationalActionResponse,
    OperationalWorkspaceResponse,
)
from app.features.operational_workspace.service import OperationalWorkspaceReadModel
from app.features.operational_workspace.service.prioritization import prioritize_position_monitoring
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_runtime import build_warrant_quote_resolver

router = APIRouter(prefix="/api/v1/operational-workspace", tags=["operational-workspace"])

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.get("/actions", response_model=OperationalWorkspaceResponse)
async def list_operational_actions(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> OperationalWorkspaceResponse:
    actions = await OperationalWorkspaceReadModel(session).list_actions(workspace_id=WORKSPACE_ID)
    health_service = PositionMonitoringHealthService(
        database=container.database,
        market_data=container.eodhd.adapter if container.eodhd is not None else None,
        max_completed_price_age_days=(
            container.settings.position_monitoring.max_completed_price_age_days
        ),
    )
    valuation_service = ProductPositionValuationService(
        database=container.database,
        quote_resolver=build_warrant_quote_resolver(container),
    )
    actions = await prioritize_position_monitoring(
        actions,
        health_reader=health_service.for_trade,
        valuation_reader=valuation_service.for_trade,
    )
    return OperationalWorkspaceResponse(
        generated_at=datetime.now(UTC),
        actions=[OperationalActionResponse(**asdict(action)) for action in actions],
    )
