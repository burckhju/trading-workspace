"""FT-013 REST API."""

from fastapi import APIRouter

from app.features.model.api.hypothesis_proposal_router import router as hypothesis_proposal_router
from app.features.model.api.lesson_hypothesis_router import router as lesson_hypothesis_router
from app.features.model.api.proposal_validation_router import router as proposal_validation_router
from app.features.model.api.router import router as governance_router

router = APIRouter()
router.include_router(governance_router)
router.include_router(lesson_hypothesis_router)
router.include_router(hypothesis_proposal_router)
router.include_router(proposal_validation_router)

__all__ = ["router"]
