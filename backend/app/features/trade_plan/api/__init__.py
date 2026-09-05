"""FT-007 TradePlan API package."""

from fastapi import APIRouter

from app.features.trade_plan.api.overview_router import router as overview_router
from app.features.trade_plan.api.router import router as trade_plan_router

router = APIRouter()
router.include_router(trade_plan_router)
router.include_router(overview_router)

__all__ = ["router"]
