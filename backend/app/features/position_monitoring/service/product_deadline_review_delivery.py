"""Read-only prerequisite recheck at the existing pre-dispatch trade lock."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.features.position_monitoring.domain.product_deadline_review import (
    RULE_SCOPE,
    RULE_VERSION,
    decide_product_deadline_review,
)
from app.features.position_monitoring.service.hebeltrader_loss import _owner_snapshot
from app.features.position_monitoring.service.product_deadline_review import (
    product_deadline_event_key,
)
from app.features.position_monitoring.service.product_deadline_review_inputs import (
    read_product_deadline_inputs,
)


async def deadline_review_delivery_problem(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    price_context: dict[str, str | None] | None,
    known_at: datetime,
) -> str | None:
    """Return a suppression reason, without writing or refreshing any evidence.

    Caller holds the same trade lock used by execution writers and applies the
    existing durable suppression owner. A distinct repeatable read protects
    this check from mixing Product/calendar revisions, including with pool=1.
    Already-started external requests retain the existing delivery boundary.
    """
    context = price_context or {}
    if context.get("scope") != RULE_SCOPE:
        return None
    if context.get("rule_version") != RULE_VERSION:
        return "REVIEW_ALERT_INVALIDATED"
    if known_at.utcoffset() is None:
        raise ValueError("Deadline delivery validation requires an aware clock")
    engine = session.bind
    if not isinstance(engine, AsyncEngine):
        raise RuntimeError("Deadline delivery validation requires an engine-backed session")
    async with _owner_snapshot(engine) as snapshot:
        inputs = await read_product_deadline_inputs(
            snapshot,
            workspace_id=workspace_id,
            trade_id=trade_id,
            position_id=position_id,
            now=known_at,
        )
    decision = decide_product_deadline_review(
        closed=inputs.closed, calculation=inputs.calculation, input_problems=inputs.problems
    )
    if decision.outcome == "CLOSED":
        return "REVIEW_POSITION_CLOSED"
    if context.get("episode_kind") == "DATA_UNAVAILABLE":
        return None if decision.outcome == "UNAVAILABLE" else "REVIEW_ALERT_RESOLVED"
    if context.get("episode_kind") != "DEADLINE_REVIEW":
        return "REVIEW_ALERT_INVALIDATED"
    if decision.outcome == "UNAVAILABLE":
        return "REVIEW_DEADLINE_INPUTS_UNAVAILABLE"
    current_key = product_deadline_event_key(inputs, decision)
    if current_key is None or context.get("deadline_event_key") != current_key:
        return "REVIEW_ALERT_RESOLVED"
    return None
