"""FT-009 Trade & Position API package."""

from fastapi import APIRouter

from app.features.trade_position.api.read_router import router as read_router
from app.features.trade_position.api.router import router as command_router

router = APIRouter()
router.include_router(command_router)
router.include_router(read_router)

__all__ = ["router"]
