"""FT-013 REST API."""

from fastapi import APIRouter

from app.features.model.api.lesson_hypothesis_router import router as lesson_hypothesis_router
from app.features.model.api.router import router as governance_router

router = APIRouter()
router.include_router(governance_router)
router.include_router(lesson_hypothesis_router)

__all__ = ["router"]
