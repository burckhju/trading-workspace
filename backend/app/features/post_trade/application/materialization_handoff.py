"""FT-011-owned, inspected handoff; optional locks live in the caller's transaction.

The FT-012 command may transport this handoff, but never decides review currentness.
No method here commits, revalidates a review or writes an economic fact.
"""

from dataclasses import replace
from typing import Protocol
from uuid import UUID

from app.features.post_trade.application.exit_review_service import ExitReviewService
from app.features.post_trade.application.handoff_service import Ft012Handoff, Ft012HandoffService
from app.features.post_trade.domain import ExitReviewCurrentness


class Ft011SourceBusyError(RuntimeError):
    """A concurrent source transaction owns a required lock; explicit retry is safe."""


class MaterializationSourceGuard(Protocol):
    async def acquire(self, *, workspace_id: UUID, trade_id: UUID) -> None: ...


class InspectedFt012HandoffService:
    def __init__(
        self,
        *,
        handoff: Ft012HandoffService,
        inspector: ExitReviewService,
        guard: MaterializationSourceGuard | None = None,
    ) -> None:
        self._handoff, self._inspector, self._guard = handoff, inspector, guard

    async def get(self, *, workspace_id: UUID, trade_id: UUID) -> Ft012Handoff:
        if self._guard is not None:
            await self._guard.acquire(workspace_id=workspace_id, trade_id=trade_id)
        handoff = await self._handoff.get(workspace_id=workspace_id, trade_id=trade_id)
        if not handoff.ready or handoff.exit_review_version_id is None:
            return handoff
        currentness = await self._inspector.inspect_version_currentness(
            workspace_id=workspace_id, version_id=handoff.exit_review_version_id
        )
        if currentness is ExitReviewCurrentness.CURRENT:
            return handoff
        return replace(
            handoff,
            ready=False,
            reason=("EXIT_REVIEW_STALE" if currentness else "EXIT_REVIEW_SOURCE_UNKNOWN"),
        )
