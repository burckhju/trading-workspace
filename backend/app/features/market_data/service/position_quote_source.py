"""Deterministic, persistent quote-source selection for an open position."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
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
AUTO_SELECTION_POLICY = "VERIFIED_ROUTE_RECONCILIATION_V1"
_RETRYABLE_REASONS = frozenset(
    {
        "NO_VERIFIED_QUOTE_SOURCE",
        "NO_VERIFIED_QUOTE_SOURCE_FOR_CURRENCY",
        "NO_ALLOWED_VERIFIED_QUOTE_SOURCE",
        "MULTIPLE_VERIFIED_QUOTE_SOURCES",
    }
)
_UNIQUE_REASONS = frozenset(
    {
        "UNIQUE_VERIFIED_ROUTE",
        "UNIQUE_VERIFIED_ROUTE_ON_PREFERRED_LISTING",
    }
)


@dataclass(frozen=True, slots=True)
class SourceReconciliation:
    selection: PositionQuoteSourceSelectionModel | None
    changed: bool
    reason: str


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
    """Select verified routes without network I/O; preserve existing selected routes."""

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

        return await self._create(
            workspace_id=workspace_id,
            position_id=position_id,
            warrant_id=warrant_id,
            preferred_listing_id=preferred_listing_id,
            expected_currency=expected_currency,
            selected_at=selected_at,
        )

    async def reconcile(
        self,
        *,
        workspace_id: UUID,
        position_id: UUID,
        warrant_id: UUID,
        selected_at: datetime | None = None,
    ) -> SourceReconciliation:
        """Retry automatic negative decisions and repair a verified issuer's policy.

        All callers serialize on the position lock, including select_once. An
        existing selected route is never switched, even if it becomes unavailable.
        Unknown/manual policies and malformed historical constraints are preserved.
        """
        if not await self.repository.lock_open_position(workspace_id, position_id, warrant_id):
            return SourceReconciliation(None, False, "OPEN_POSITION_NOT_FOUND")
        old = await self.repository.active_for_position(workspace_id, position_id)
        preferred = None
        currency = None
        candidates = None
        if old is not None:
            if old.policy_version != POSITION_QUOTE_SOURCE_POLICY_V1:
                return SourceReconciliation(old, False, "EXISTING_POLICY_PRESERVED")
            if old.selection_status == "SELECTED":
                if (
                    old.provider not in ISSUER_INDICATIONS
                    or old.selection_reason not in _UNIQUE_REASONS
                ):
                    return SourceReconciliation(old, False, "SELECTED_ROUTE_PRESERVED")
                verified = await self.repository.verified_candidates(workspace_id, warrant_id)
                candidates = tuple(
                    c
                    for c in verified
                    if (
                        c.provider in self.allowed_providers
                        and c.provider.value == old.provider
                        and c.listing_id == old.warrant_listing_id
                        and c.mapping_id == old.warrant_provider_mapping_id
                        and c.mapping_version == old.mapping_version
                        and c.identity_key == old.identity_key
                    )
                )
                if len(candidates) != 1:
                    return SourceReconciliation(old, False, "SELECTED_IDENTITY_NOT_REVERIFIED")
            elif old.selection_reason not in _RETRYABLE_REASONS:
                return SourceReconciliation(old, False, "EXISTING_REASON_PRESERVED")
            evidence = old.evidence
            if not isinstance(evidence, dict) or evidence.get("warrant_id") != str(warrant_id):
                return SourceReconciliation(old, False, "SELECTION_CONSTRAINTS_UNVERIFIED")
            try:
                value = evidence.get("preferred_listing_id")
                preferred = UUID(value) if value is not None else None
                currency = evidence.get("expected_currency")
                if currency is not None and (
                    not isinstance(currency, str) or len(currency) != 3 or not currency.isupper()
                ):
                    raise ValueError("INVALID_CURRENCY")
            except (ValueError, TypeError, AttributeError):
                return SourceReconciliation(old, False, "SELECTION_CONSTRAINTS_UNVERIFIED")
        new = await self._create(
            workspace_id=workspace_id,
            position_id=position_id,
            warrant_id=warrant_id,
            preferred_listing_id=preferred,
            expected_currency=currency,
            selected_at=selected_at,
            previous=old,
            candidates=candidates,
            automatic=True,
        )
        return SourceReconciliation(
            new,
            new is not old,
            (
                "UNCHANGED"
                if new is old
                else (
                    "ISSUER_POLICY_RECONCILED"
                    if old is not None and old.selection_status == "SELECTED"
                    else "SOURCE_DECISION_RECONCILED"
                )
            ),
        )

    async def _create(
        self,
        *,
        workspace_id: UUID,
        position_id: UUID,
        warrant_id: UUID,
        preferred_listing_id: UUID | None,
        expected_currency: str | None,
        selected_at: datetime | None,
        previous: PositionQuoteSourceSelectionModel | None = None,
        candidates: tuple[PositionQuoteSourceCandidate, ...] | None = None,
        automatic: bool = False,
    ) -> PositionQuoteSourceSelectionModel:
        if candidates is None:
            candidates = await self.repository.verified_candidates(workspace_id, warrant_id)
        allowed_candidates = tuple(
            candidate for candidate in candidates if candidate.provider in self.allowed_providers
        )
        decision = choose_position_quote_source(
            allowed_candidates,
            preferred_listing_id=preferred_listing_id,
            expected_currency=expected_currency,
        )
        if candidates and not allowed_candidates:
            decision = PositionQuoteSourceDecision(
                PositionQuoteSourceSelectionStatus.NO_VERIFIED_QUOTE_SOURCE,
                "NO_ALLOWED_VERIFIED_QUOTE_SOURCE",
                (),
            )
        selected = decision.selected
        if previous is not None and previous.selection_status == "SELECTED" and selected is None:
            return previous
        when = selected_at or datetime.now(UTC)
        if when.utcoffset() is None:
            raise ValueError("SELECTION_TIMESTAMP_MUST_HAVE_TIMEZONE")
        if previous is not None:
            old_time = previous.selected_at
            # SQLite test storage drops the offset; production uses timestamptz.
            if old_time.utcoffset() is None:
                old_time = old_time.replace(tzinfo=UTC)
            if when < old_time:
                raise ValueError("SELECTION_CLOCK_MOVED_BACKWARDS")

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
            "warrant_id": str(warrant_id),
            "preferred_listing_id": (
                str(preferred_listing_id) if preferred_listing_id is not None else None
            ),
            "expected_currency": expected_currency,
            "allowed_providers": sorted(provider.value for provider in self.allowed_providers),
            "verified_candidates": [candidate_evidence(candidate) for candidate in candidates],
            "allowed_candidates": [
                candidate_evidence(candidate) for candidate in allowed_candidates
            ],
            "eligible_candidates": [
                candidate_evidence(candidate) for candidate in decision.candidates
            ],
            "route_selection_reason": decision.reason,
            "selection_algorithm": AUTO_SELECTION_POLICY,
            "actor": "MARKET_DATA_REFRESH" if automatic else "POSITION_CREATION",
            "previous_selection_id": str(previous.id) if previous else None,
        }
        # Keep repeated decisions idempotent; changed candidate evidence gets an
        # audited successor even if the outcome is still ambiguous or missing.
        if (
            previous is not None
            and selected is None
            and (
                previous.selection_status == decision.status.value
                and previous.selection_reason == decision.reason
                and all(
                    previous.evidence.get(key) == evidence[key]
                    for key in (
                        "warrant_id",
                        "preferred_listing_id",
                        "expected_currency",
                        "allowed_providers",
                        "verified_candidates",
                        "allowed_candidates",
                        "eligible_candidates",
                    )
                )
            )
        ):
            return previous
        contract = ISSUER_INDICATIONS.get(selected.provider.value) if selected else None
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
            selection_reason=(
                f"VERIFIED_{selected.provider.value}_ISSUER_INDICATION"
                if contract and selected
                else decision.reason
            ),
            policy_version=contract[2] if contract else POSITION_QUOTE_SOURCE_POLICY_V1,
            evidence=evidence,
            selected_at=when,
            superseded_at=None,
        )
        if previous is not None:
            await self.repository.supersede(previous, when)
        await self.repository.add(row)
        return row
