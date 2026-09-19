"""Read-only planning for legacy position quote-source backfill."""

import hashlib
import json
from collections import Counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.domain.position_quote_source import (
    PositionQuoteSourceDecision,
    PositionQuoteSourceSelectionStatus,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.persistence.position_quote_source_backfill import (
    open_position_rows,
)
from app.features.market_data.service.position_quote_source import choose_position_quote_source


def candidate_payload(candidate) -> dict[str, object]:
    return {
        "provider": candidate.provider.value,
        "listing_id": str(candidate.listing_id),
        "mapping_id": str(candidate.mapping_id) if candidate.mapping_id is not None else None,
        "mapping_version": candidate.mapping_version,
        "identity_key": candidate.identity_key,
        "currency": candidate.currency,
        "mic": candidate.mic,
        "provider_exchange_code": candidate.provider_exchange_code,
    }


def selection_payload(selection) -> dict[str, object]:
    return {
        "status": selection.selection_status,
        "reason": selection.selection_reason,
        "provider": selection.provider,
        "listing_id": (
            str(selection.warrant_listing_id)
            if selection.warrant_listing_id is not None
            else None
        ),
        "mapping_id": (
            str(selection.warrant_provider_mapping_id)
            if selection.warrant_provider_mapping_id is not None
            else None
        ),
        "mapping_version": selection.mapping_version,
        "identity_key": selection.identity_key,
    }


def decision_payload(decision: PositionQuoteSourceDecision) -> dict[str, object]:
    selected = decision.selected
    return {
        "status": decision.status.value,
        "reason": decision.reason,
        "provider": selected.provider.value if selected is not None else None,
        "listing_id": str(selected.listing_id) if selected is not None else None,
        "mapping_id": (
            str(selected.mapping_id)
            if selected is not None and selected.mapping_id is not None
            else None
        ),
        "mapping_version": selected.mapping_version if selected is not None else None,
        "identity_key": selected.identity_key if selected is not None else None,
    }


def preview_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def build_backfill_preview(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    allowed_providers: frozenset[MarketDataProvider],
) -> dict[str, object]:
    rows = await open_position_rows(session, workspace_id)
    repository = PositionQuoteSourceSelectionRepository(session)
    plans: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for position, trade, warrant, evaluation, provenance_listing, existing in rows:
        preferred = evaluation.warrant_listing_id if evaluation else None
        currency = provenance_listing.quotation_currency_code if provenance_listing else None
        base = {
            "position_id": str(position.id),
            "trade_id": str(trade.id),
            "warrant_id": str(warrant.id),
            "isin": warrant.isin,
            "preferred_listing_id": str(preferred) if preferred else None,
            "expected_currency": currency,
        }
        if existing is not None:
            counts[f"EXISTING_{existing.selection_status}"] += 1
            plans.append(
                {
                    **base,
                    "action": "EXISTING_SELECTION",
                    "decision": selection_payload(existing),
                    "verified_candidates": [],
                    "allowed_candidates": [],
                }
            )
            continue

        candidates = await repository.verified_candidates(workspace_id, warrant.id)
        allowed = tuple(
            item for item in candidates if item.provider in allowed_providers
        )
        decision = choose_position_quote_source(
            allowed,
            preferred_listing_id=preferred,
            expected_currency=currency,
        )
        if candidates and not allowed:
            decision = PositionQuoteSourceDecision(
                PositionQuoteSourceSelectionStatus.NO_VERIFIED_QUOTE_SOURCE,
                "NO_ALLOWED_VERIFIED_QUOTE_SOURCE",
                (),
            )
        counts[decision.status.value] += 1
        plans.append(
            {
                **base,
                "action": "CREATE_SELECTION",
                "decision": decision_payload(decision),
                "verified_candidates": [candidate_payload(item) for item in candidates],
                "allowed_candidates": [candidate_payload(item) for item in allowed],
            }
        )

    canonical = {
        "workspace_id": str(workspace_id),
        "allowed_providers": sorted(item.value for item in allowed_providers),
        "positions": plans,
    }
    return {
        **canonical,
        "preview_sha256": preview_digest(canonical),
        "summary": {
            "open_positions": len(rows),
            "legacy_to_create": sum(
                plan["action"] == "CREATE_SELECTION" for plan in plans
            ),
            "existing": sum(
                plan["action"] == "EXISTING_SELECTION" for plan in plans
            ),
            "selected": counts["SELECTED"],
            "no_verified_quote_source": counts["NO_VERIFIED_QUOTE_SOURCE"],
            "ambiguous_source": counts["AMBIGUOUS_SOURCE"],
        },
    }
