from app.features.position_monitoring.api.frankfurt import router as frankfurt_router
from app.features.position_monitoring.api.router import router

router.include_router(frankfurt_router)

__all__ = ["router"]
