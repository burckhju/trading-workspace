"""Read-only trading-venue reconciliation for provider instrument mappings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.errors import MarketDataNotFoundError
from app.features.market_data.service.unit_of_work import MarketDataUnitOfWork


class VenueReconciliationStatus(StrEnum):
    """Outcome of reconciling provider exchange evidence with one listing venue."""

    MATCHED = "MATCHED"
    CONFLICT = "CONFLICT"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class VenueReconciliationResult:
    """Explain provider-exchange evidence without changing reference master data."""

    status: VenueReconciliationStatus
    listing_venue_id: UUID | None
    evidence_venue_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class VerifiedListingVenue:
    """Provider-verified evidence for one listing, never a global exchange alias."""

    workspace_id: UUID
    listing_id: UUID
    provider: MarketDataProvider
    provider_exchange_code: str
    venue_id: UUID


class ProviderVenueReconciliationService:
    """Prefer scoped instrument evidence; otherwise explain historical mapping evidence."""

    def __init__(
        self, uow: MarketDataUnitOfWork, *, verified_listing: VerifiedListingVenue | None = None
    ) -> None:
        self._uow = uow
        self._verified_listing = verified_listing

    async def reconcile_mapping(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> VenueReconciliationResult:
        """Explain one persisted listing mapping without mutating reference data."""
        async with self._uow:
            mapping = await self._uow.mappings.get(workspace_id, mapping_id)
            if mapping is None:
                raise MarketDataNotFoundError("Provider mapping not found")
            if mapping.listing_id is None:
                raise MarketDataNotFoundError(
                    "Provider mapping is not managed by the listing reconciliation path"
                )
            return await self.reconcile(
                workspace_id,
                mapping.listing_id,
                mapping.provider,
                mapping.provider_exchange_code,
            )

    async def reconcile(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        provider: MarketDataProvider,
        provider_exchange_code: str,
    ) -> VenueReconciliationResult:
        """Return evidence; never create or mutate a trading venue."""
        listing_venue_id = await self._uow.mappings.get_listing_venue_id(workspace_id, listing_id)
        if listing_venue_id is None:
            return VenueReconciliationResult(
                status=VenueReconciliationStatus.UNRESOLVED,
                listing_venue_id=None,
                evidence_venue_ids=(),
            )

        verified = self._verified_listing
        if verified is not None and (
            workspace_id,
            listing_id,
            provider,
            provider_exchange_code,
        ) == (
            verified.workspace_id,
            verified.listing_id,
            verified.provider,
            verified.provider_exchange_code,
        ):
            return VenueReconciliationResult(
                (
                    VenueReconciliationStatus.MATCHED
                    if listing_venue_id == verified.venue_id
                    else VenueReconciliationStatus.CONFLICT
                ),
                listing_venue_id,
                (verified.venue_id,),
            )

        evidence = tuple(
            sorted(
                set(
                    await self._uow.mappings.list_active_venue_ids_for_exchange(
                        workspace_id,
                        provider,
                        provider_exchange_code,
                    )
                ),
                key=str,
            )
        )
        if not evidence:
            status = VenueReconciliationStatus.UNRESOLVED
        elif len(evidence) > 1:
            status = VenueReconciliationStatus.AMBIGUOUS
        elif evidence[0] == listing_venue_id:
            status = VenueReconciliationStatus.MATCHED
        else:
            status = VenueReconciliationStatus.CONFLICT
        return VenueReconciliationResult(status, listing_venue_id, evidence)
