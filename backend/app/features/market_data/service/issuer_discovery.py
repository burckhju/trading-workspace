"""Discover exact issuer identities without replacing mappings or creating master data."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DatabaseManager
from app.features.market.contracts import is_canonical_isin
from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.product.domain.models import ProductFamily, WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.issuer_pages import IssuerPageClient, provider_for_issuer
from app.providers.morganstanley.products import EXCLUDED_PRODUCTS


@dataclass(frozen=True)
class Candidate:
    isin: str
    listing_id: UUID
    warrant_version: int
    listing_version: int
    issuer_id: UUID
    issuer_version: int
    venue_id: UUID
    venue_version: int


def blocked(reason: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "reason": reason, "mapping_created": False}


async def inspect_candidate(
    session: AsyncSession,
    workspace_id: UUID,
    warrant_id: UUID,
    provider: MarketDataProvider,
    *,
    lock: bool = False,
) -> Candidate | dict[str, Any]:
    query = (
        select(WarrantModel, IssuerModel)
        .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
        .where(WarrantModel.id == warrant_id, WarrantModel.workspace_id == workspace_id)
    )
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).one_or_none()
    if row is None:
        return blocked("ISSUER_PRODUCT_NOT_IN_WORKSPACE")
    warrant, issuer = row
    if (
        warrant.lifecycle_status != WarrantLifecycle.ACTIVE
        or not issuer.is_active
        or warrant.product_family != ProductFamily.WARRANT
        or provider_for_issuer(issuer.legal_name) != provider.value
    ):
        return blocked("ISSUER_PRODUCT_NOT_ELIGIBLE")
    if not is_canonical_isin(warrant.isin):
        return {
            **blocked("ISSUER_ISIN_INVALID"),
            "status": "NEEDS_MASTER_DATA",
            "required_action": "VERIFY_ORIGINAL_PRODUCT_IDENTIFIER",
        }
    if warrant.wkn and warrant.wkn != warrant.isin[5:11]:
        return blocked("ISSUER_PRODUCT_IDENTITY_CONFLICT")
    if provider == MarketDataProvider.MORGAN_STANLEY and warrant.isin in EXCLUDED_PRODUCTS:
        return blocked(EXCLUDED_PRODUCTS[warrant.isin])
    listing_query = (
        select(WarrantListingModel, TradingVenueModel)
        .join(TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id)
        .join(CurrencyModel, CurrencyModel.code == WarrantListingModel.quotation_currency_code)
        .where(
            WarrantListingModel.workspace_id == workspace_id,
            WarrantListingModel.warrant_id == warrant_id,
            WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
            WarrantListingModel.quotation_currency_code == "EUR",
            TradingVenueModel.is_active.is_(True),
            CurrencyModel.is_active.is_(True),
        )
    )
    if lock:
        listing_query = listing_query.with_for_update()
    listings = (await session.execute(listing_query)).all()
    # Include inactive listings: an existing disabled route must not be bypassed.
    all_listing_ids = select(WarrantListingModel.id).where(
        WarrantListingModel.warrant_id == warrant_id
    )
    mappings = list(
        await session.scalars(
            select(WarrantProviderMappingModel).where(
                WarrantProviderMappingModel.provider == provider,
                or_(
                    WarrantProviderMappingModel.provider_symbol == warrant.isin,
                    WarrantProviderMappingModel.warrant_listing_id.in_(all_listing_ids),
                ),
            )
        )
    )
    if mappings:
        if len(mappings) == 1:
            mapping = mappings[0]
            for listing, venue in listings:
                if verified_identity(workspace_id, listing, warrant, venue, provider, mapping):
                    return {
                        "status": "AVAILABLE",
                        "reason": "ISSUER_EXISTING_ROUTE_PRESERVED",
                        "mapping_id": str(mapping.id),
                        "mapping_created": False,
                    }
        return blocked("ISSUER_EXISTING_MAPPING_REQUIRES_REVIEW")
    if len(listings) != 1:
        total = len(
            list(
                await session.scalars(
                    select(WarrantListingModel.id).where(
                        WarrantListingModel.workspace_id == workspace_id,
                        WarrantListingModel.warrant_id == warrant_id,
                    )
                )
            )
        )
        reason = (
            "ISSUER_LISTING_MISSING"
            if total == 0
            else (
                "ISSUER_NO_ACTIVE_EUR_LISTING"
                if not listings
                else "ISSUER_MULTIPLE_ACTIVE_EUR_LISTINGS"
            )
        )
        return {
            **blocked(reason),
            "status": "NEEDS_MASTER_DATA",
            "listing_count": total,
            "eligible_listing_count": len(listings),
            "required_action": "REVIEW_VERIFIED_VENUE_AND_CURRENCY",
        }
    listing, venue = listings[0]
    return Candidate(
        warrant.isin,
        listing.id,
        warrant.version,
        listing.version,
        issuer.id,
        issuer.version,
        venue.id,
        venue.version,
    )


async def discover_issuer_route(
    database: DatabaseManager,
    pages: IssuerPageClient,
    workspace_id: UUID,
    warrant_id: UUID,
    provider: MarketDataProvider,
) -> dict[str, Any]:
    """No HTTP while holding a transaction; lock and revalidate before creating a route."""
    async with database.session_context() as session:
        before = await inspect_candidate(session, workspace_id, warrant_id, provider)
    if isinstance(before, dict):
        return before
    evidence = await pages.fetch(provider.value, before.isin)
    if evidence.provider != provider.value or evidence.isin != before.isin:
        return blocked("ISSUER_PRODUCT_IDENTITY_CONFLICT")
    try:
        async with database.session_context() as session:
            current = await inspect_candidate(
                session, workspace_id, warrant_id, provider, lock=True
            )
            if isinstance(current, dict):
                return current
            if current != before:
                return blocked("ISSUER_MASTER_DATA_CHANGED_DURING_DISCOVERY")
            now = datetime.now(UTC)
            payload = {
                **evidence.payload(),
                "workspace_id": str(workspace_id),
                "warrant_id": str(warrant_id),
                "warrant_version": before.warrant_version,
                "listing_id": str(before.listing_id),
                "listing_version": before.listing_version,
                "mapping_version": 1,
            }
            from app.features.market_data.domain.issuer_route_evidence import evidence_stream_id

            if not evidence_stream_id(
                payload,
                provider=provider.value,
                isin=before.isin,
                currency="EUR",
                workspace_id=str(workspace_id),
                warrant_id=str(warrant_id),
                warrant_version=before.warrant_version,
                listing_id=str(before.listing_id),
                listing_version=before.listing_version,
                mapping_version=1,
            ):
                return blocked("ISSUER_PAGE_EVIDENCE_INVALID")
            mapping = WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=workspace_id,
                warrant_listing_id=before.listing_id,
                provider=provider,
                provider_symbol=before.isin,
                provider_exchange_code="ISSUER",
                status=MappingStatus.ACTIVE,
                validated_at=now,
                validation_message="VERIFIED_OFFICIAL_ISSUER_PRODUCT_PAGE_V1",
                identity_evidence=payload,
                created_at=now,
                updated_at=now,
                version=1,
            )
            session.add(mapping)
            mapping_id = str(mapping.id)
            await session.commit()
    except IntegrityError:
        # A concurrent registration/global identity conflict cannot steal another route.
        return blocked("ISSUER_CONCURRENT_MAPPING_CONFLICT")
    return {
        "status": "AVAILABLE",
        "reason": "ISSUER_PRODUCT_ROUTE_VERIFIED",
        "provider": provider.value,
        "mapping_id": mapping_id,
        "warrant_listing_id": str(before.listing_id),
        "mapping_created": True,
        "evidence_schema": evidence.schema_version,
        "source_sha256": evidence.source_sha256,
    }
