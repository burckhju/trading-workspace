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
from app.features.market.persistence.models import UnderlyingModel
from app.features.product.persistence.models import WarrantModel
from app.features.product_selection.persistence.models import (
    ProductEvaluationModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
)
from app.features.trade_plan.domain.enums import TradePlanOriginType, TradePlanStatus
from app.features.trade_plan.persistence.models import TradePlanModel, TradePlanVersionModel
from app.features.trade_plan.service.execution_overview import (
    PlanExecutionOverview,
    read_execution_overviews,
)

router = APIRouter(prefix="/api/v1/trade-plans", tags=["trade-plans"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


class SelectedProductOverviewResponse(BaseModel):
    """Latest explicit selection of this exact plan version; names are current master data."""

    run_id: UUID
    product_evaluation_id: UUID
    warrant_id: UUID
    display_name: str | None
    isin: str | None
    wkn: str | None


class TradePlanOverviewItemResponse(BaseModel):
    id: UUID
    underlying_id: UUID
    origin_type: TradePlanOriginType
    created_at: datetime
    latest_version_id: UUID
    latest_version: int
    status: TradePlanStatus
    underlying_name: str | None = None
    underlying_isin: str | None = None
    underlying_wkn: str | None = None
    selected_product: SelectedProductOverviewResponse | None = None
    execution: PlanExecutionOverview | None = None


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
    # One set-based read, not a request/query per plan or per historical run.
    # An unselected newer run is not a selection; an older plan version cannot
    # supply a product for the current version. Never infer a choice from rank.
    selections = (
        select(
            ProductSelectionRunModel.trade_plan_id,
            ProductSelectionRunModel.trade_plan_version_id,
            ProductSelectionRunModel.id.label("run_id"),
            ProductEvaluationModel.id.label("evaluation_id"),
            ProductEvaluationModel.warrant_id,
            func.row_number()
            .over(
                partition_by=(
                    ProductSelectionRunModel.trade_plan_id,
                    ProductSelectionRunModel.trade_plan_version_id,
                ),
                order_by=(
                    ProductSelectionModel.selected_at.desc(),
                    ProductSelectionModel.id.desc(),
                ),
            )
            .label("selection_rank"),
        )
        .select_from(ProductSelectionRunModel)
        .join(ProductSelectionModel, ProductSelectionModel.run_id == ProductSelectionRunModel.id)
        .join(
            ProductEvaluationModel,
            and_(
                ProductEvaluationModel.id == ProductSelectionModel.product_evaluation_id,
                ProductEvaluationModel.run_id == ProductSelectionRunModel.id,
            ),
        )
        .where(ProductSelectionRunModel.workspace_id == WORKSPACE_ID)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                TradePlanModel,
                TradePlanVersionModel,
                UnderlyingModel,
                selections.c.run_id,
                selections.c.evaluation_id,
                selections.c.warrant_id,
                WarrantModel,
            )
            .select_from(TradePlanModel)
            .join(
                TradePlanVersionModel,
                and_(
                    TradePlanVersionModel.trade_plan_id == TradePlanModel.id,
                    TradePlanVersionModel.version == latest_version_number,
                ),
            )
            .outerjoin(
                UnderlyingModel,
                and_(
                    UnderlyingModel.id == TradePlanModel.underlying_id,
                    UnderlyingModel.workspace_id == TradePlanModel.workspace_id,
                ),
            )
            .outerjoin(
                selections,
                and_(
                    selections.c.trade_plan_id == TradePlanModel.id,
                    selections.c.trade_plan_version_id == TradePlanVersionModel.id,
                    selections.c.selection_rank == 1,
                ),
            )
            .outerjoin(
                WarrantModel,
                and_(
                    WarrantModel.id == selections.c.warrant_id,
                    WarrantModel.workspace_id == TradePlanModel.workspace_id,
                    WarrantModel.underlying_id == TradePlanModel.underlying_id,
                ),
            )
            .where(TradePlanModel.workspace_id == WORKSPACE_ID)
            .order_by(TradePlanModel.created_at.desc(), TradePlanModel.id)
        )
    ).all()
    executions = await read_execution_overviews(
        session,
        workspace_id=WORKSPACE_ID,
        current_versions={row[0].id: row[1].id for row in rows},
    )
    return [
        TradePlanOverviewItemResponse(
            id=plan.id,
            underlying_id=plan.underlying_id,
            origin_type=plan.origin_type,
            created_at=plan.created_at,
            latest_version_id=version.id,
            latest_version=version.version,
            status=version.status,
            execution=executions[plan.id],
            underlying_name=underlying.name if underlying else None,
            underlying_isin=underlying.isin if underlying else None,
            underlying_wkn=underlying.wkn if underlying else None,
            selected_product=(
                SelectedProductOverviewResponse(
                    run_id=run_id,
                    product_evaluation_id=evaluation_id,
                    warrant_id=warrant_id,
                    display_name=product.display_name if product else None,
                    isin=product.isin if product else None,
                    wkn=product.wkn if product else None,
                )
                if run_id is not None
                else None
            ),
        )
        for plan, version, underlying, run_id, evaluation_id, warrant_id, product in rows
    ]
