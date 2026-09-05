"""Read-only TradePlan overview for workspace navigation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.trade_plan.domain.enums import TradePlanOriginType, TradePlanStatus
from app.features.trade_plan.persistence.models import TradePlanModel, TradePlanVersionModel

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


class TradePlanOverviewItemResponse(BaseModel):
    id: UUID
    underlying_id: UUID
    origin_type: TradePlanOriginType
    created_at: datetime
    latest_version_id: UUID
    latest_version: int
    status: TradePlanStatus


@router.get("", response_model=list[TradePlanOverviewItemResponse])
async def list_trade_plans(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[TradePlanOverviewItemResponse]:
    latest_version_number = (
        select(func.max(TradePlanVersionModel.version))
        .where(TradePlanVersionModel.trade_plan_id == TradePlanModel.id)
        .correlate(TradePlanModel)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(TradePlanModel, TradePlanVersionModel)
            .join(
                TradePlanVersionModel,
                and_(
                    TradePlanVersionModel.trade_plan_id == TradePlanModel.id,
                    TradePlanVersionModel.version == latest_version_number,
                ),
            )
            .where(TradePlanModel.workspace_id == WORKSPACE_ID)
            .order_by(TradePlanModel.created_at.desc(), TradePlanModel.id)
        )
    ).all()
    return [
        TradePlanOverviewItemResponse(
            id=plan.id,
            underlying_id=plan.underlying_id,
            origin_type=plan.origin_type,
            created_at=plan.created_at,
            latest_version_id=version.id,
            latest_version=version.version,
            status=version.status,
        )
        for plan, version in rows
    ]
