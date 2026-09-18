"""Deterministic, persistent quote-source selection for an open position."""

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.domain.position_quote_source import (
    PositionQuoteSourceCandidate,
    PositionQuoteSourceDecision,
    PositionQuoteSourceSelectionStatus,
)
from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)

POSITION_QUOTE_SOURCE_POLICY_V1 = "POSITION_QUOTE_SOURCE_POLICY_V1"


def choose_position_quote_source(
    candidates: Iterable[PositionQuoteSourceCandidate],
    *,
    preferred_listing_id: UUID | None = None,
    expected_currency: str | None = None,
) -> PositionQuoteSourceDecision:
    """Choose only when verified evidence leaves exactly one eligible route."""

    eligible = list(candidates)
    if expected_currency is not None:
        currency_matches = [
            candidate for candidate in eligible if candidate.currency == expected_currency
        ]
        if eligible and not currency_matches:
            return PositionQuoteSourceDecision(
                PositionQuoteSourceSelectionStatus.NO_VERIFIED_QUOTE_SOURCE,
                "NO_VERIFIED_QUOTE_SOURCE_FOR_CURRENCY",
                (),
            )
        eligible = currency_matches

    if preferred_listing_id is not None:
        preferred = [
            candidate for candidate in eligible if candidate.listing_id == preferred_listing_id
        ]
        if preferred:
            eligible = preferred

    unique = {
        (
            candidate.provider,
            candidate.listing_id,
            candidate.mapping_id,
            candidate.identity_key,
        ): candidate
        for candidate in eligible
    }
    ordered = tuple(
        sorted(
            unique.values(),
            key=lambda candidate: (
                candidate.provider.value,
                str(candidate.listing_id),
                str(candidate.mapping_id or ""),
                candidate.identity_key,
            ),
        )
    )

    if not ordered:
        return PositionQuoteSourceDecision(
            PositionQuoteSourceSelectionStatus.NO_VERIFIED_QUOTE_SOURCE,
            "NO_VERIFIED_QUOTE_SOURCE",
            (),
        )
    if len(ordered) != 1:
        return PositionQuoteSourceDecision(
            PositionQuoteSourceSelectionStatus.AMBIGUOUS_SOURCE,
            "MULTIPLE_VERIFIED_QUOTE_SOURCES",
            ordered,
        )
    reason = (
        "UNIQUE_VERIFIED_ROUTE_ON_PREFERRED_LISTING"
        if preferred_listing_id is not None and ordered[0].listing_id == preferred_listing_id
        else "UNIQUE_VERIFIED_ROUTE"
    )
    return PositionQuoteSourceDecision(
        PositionQuoteSourceSelectionStatus.SELECTED,
        reason,
        ordered,
        ordered[0],
    )


class PositionQuoteSourceSelector:
    """Persist the first source decision; network I/O and discovery are intentionally absent."""

    def __init__(
        self,
        repository: PositionQuoteSourceSelectionRepository,
        allowed_providers: Iterable[MarketDataProvider],
    ) -> None:
        self.repository = repository
        self.allowed_providers = frozenset(allowed_providers)

    async def select_once(
        self,
        *,
        workspace_id: UUID,
        position_id: UUID,
        warrant_id: UUID,
        preferred_listing_id: UUID | None = None,
        expected_currency: str | None = None,
        selected_at: datetime | None = None,
    ) -> PositionQuoteSourceSelectionModel:
        if not await self.repository.lock_open_position(workspace_id, position_id, warrant_id):
            raise ValueError("OPEN_POSITION_NOT_FOUND")

        existing = await self.repository.active_for_position(workspace_id, position_id)
        if existing is not None:
            return existing

        candidates = await self.repository.verified_candidates(
            workspace_id, warrant_id, self.allowed_providers
        )
        decision = choose_position_quote_source(
            candidates,
            preferred_listing_id=preferred_listing_id,
            expected_currency=expected_currency,
        )
        selected = decision.selected
        when = selected_at or datetime.now(UTC)

        def candidate_evidence(candidate: PositionQuoteSourceCandidate) -> dict[str, object]:
            return {
                "provider": candidate.provider.value,
                "listing_id": str(candidate.listing_id),
                "mapping_id": (
                    str(candidate.mapping_id) if candidate.mapping_id is not None else None
                ),
                "mapping_version": candidate.mapping_version,
                "identity_key": candidate.identity_key,
                "currency": candidate.currency,
                "mic": candidate.mic,
                "provider_exchange_code": candidate.provider_exchange_code,
            }

        evidence = {
            "preferred_listing_id": (
                str(preferred_listing_id) if preferred_listing_id is not None else None
            ),
            "expected_currency": expected_currency,
            "allowed_providers": sorted(provider.value for provider in self.allowed_providers),
            "verified_candidates": [candidate_evidence(candidate) for candidate in candidates],
            "eligible_candidates": [
                candidate_evidence(candidate) for candidate in decision.candidates
            ],
        }
        row = PositionQuoteSourceSelectionModel(
            id=uuid4(),
            workspace_id=workspace_id,
            position_id=position_id,
            warrant_listing_id=selected.listing_id if selected is not None else None,
            warrant_provider_mapping_id=selected.mapping_id if selected is not None else None,
            provider=selected.provider.value if selected is not None else None,
            identity_key=selected.identity_key if selected is not None else None,
            mapping_version=selected.mapping_version if selected is not None else None,
            selection_status=decision.status.value,
            selection_reason=decision.reason,
            policy_version=POSITION_QUOTE_SOURCE_POLICY_V1,
            evidence=evidence,
            selected_at=when,
            superseded_at=None,
        )
        await self.repository.add(row)
        return row
