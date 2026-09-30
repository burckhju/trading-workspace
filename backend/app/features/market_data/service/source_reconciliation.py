"""Reconsider position bindings using local verified routes, with no provider requests."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING
from uuid import UUID

from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import (
    AUTO_SELECTION_POLICY,
    PositionQuoteSourceSelector,
)
from app.features.market_data.service.provider_eligibility import allowed_warrant_quote_providers

if TYPE_CHECKING:
    from app.core.di import ApplicationContainer


async def reconcile_warrant_positions(
    container: ApplicationContainer, workspace_id: UUID, warrant_id: UUID
) -> dict[str, object]:
    """Position locks serialize concurrent issuer/exchange jobs and purchases.

    The independent transaction finishes before quote retrieval. Existing selected
    routes and the user's trade, execution and rule records are not rewritten.
    """
    reasons: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    changed = 0
    async with container.database.session_context() as session:
        repository = PositionQuoteSourceSelectionRepository(session)
        selector = PositionQuoteSourceSelector(
            repository, allowed_warrant_quote_providers(container)
        )
        positions = await repository.open_positions(workspace_id, warrant_id)
        for position_id in positions:
            result = await selector.reconcile(
                workspace_id=workspace_id, position_id=position_id, warrant_id=warrant_id
            )
            changed += result.changed
            reasons[result.reason] += 1
            if result.selection is not None:
                statuses[result.selection.selection_status] += 1
        await session.commit()
    return {
        "policy": AUTO_SELECTION_POLICY,
        "positions_checked": len(positions),
        "decisions_changed": changed,
        "statuses": dict(statuses),
        "reasons": dict(reasons),
    }
