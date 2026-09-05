"""FT-007 TradePlan API package."""

from app.features.trade_plan.api.overview_router import router as overview_router
from app.features.trade_plan.api.router import router

router.include_router(overview_router)

__all__ = ["router"]
