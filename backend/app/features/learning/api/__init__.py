"""FT-012 Learning REST API plus external-observation bulk imports."""

from fastapi import APIRouter

from app.features.learning.api.bulk_import_router import router as bulk_import_router
from app.features.learning.api.materialization_router import router as materialization_router
from app.features.learning.api.router import router as learning_router

router = APIRouter()
router.include_router(learning_router)
router.include_router(materialization_router)
router.include_router(bulk_import_router)

__all__ = ["router"]
