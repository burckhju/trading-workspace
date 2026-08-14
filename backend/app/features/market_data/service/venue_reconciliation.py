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


class ProviderVenueReconciliationService:
    """Reconcile provider codes using existing active mappings as evidence only."""

    def __init__(self, uow: MarketDataUnitOfWork) -> None:
        self._uow = uow

    async def reconcile_mapping(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> VenueReconciliationResult:
        """Explain one persisted mapping without mutating mapping or reference data."""
        async with self._uow:
            mapping = await self._uow.mappings.get(workspace_id, mapping_id)
            if mapping is None:
                raise MarketDataNotFoundError("Provider mapping not found")
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
