"""Explicit, idempotent public Frankfurt setup for an existing workspace warrant.

Dry-run by default. Only --apply writes verified reference/listing/mapping rows;
it never changes historical listings, evaluations, trades, orders or positions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.database import DatabaseManager
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.persistence.repositories import (
    SqlAlchemyWarrantProviderMappingRepository,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient, utc_now
from app.providers.frankfurt_quotes.public import (
    PUBLIC_EXCHANGE_CODE,
    assess_public_price,
)
from app.providers.frankfurt_quotes.schema import FRANKFURT_MIC, FrankfurtSourceError

DEFAULT_WORKSPACE = UUID("00000000-0000-4000-8000-000000000001")
PROVIDER = MarketDataProvider.FRANKFURT_QUOTES


async def configure_warrant(
    session: AsyncSession,
    client: FrankfurtSnapshotClient,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    apply: bool = False,
) -> dict[str, Any]:
    """Validate public identity first and commit new rows together, without overwrites."""
    if client.settings.source_mode is not FrankfurtSourceMode.PUBLIC_WEBSITE:
        raise ValueError("Setup requires Frankfurt public_website mode")
    statement = select(WarrantModel).where(
        WarrantModel.id == warrant_id, WarrantModel.workspace_id == workspace_id
    )
    warrant = await session.scalar(statement.with_for_update() if apply else statement)
    if warrant is None or warrant.lifecycle_status != WarrantLifecycle.ACTIVE or not warrant.isin:
        raise ValueError("An active warrant with ISIN in the requested workspace is required")

    price, retrieved_at, _hit = await client.load_public(warrant.isin)
    observation = assess_public_price(
        price,
        isin=warrant.isin,
        currency=price.currency.originalValue,
        now=utc_now(),
        retrieved_at=retrieved_at,
        max_age_seconds=client.settings.max_quote_age_seconds,
    )
    if not observation.analysis_usable:
        raise ValueError(f"Public instrument evidence is unusable: {observation.reason}")
    currency_code = price.currency.originalValue
    currency = await session.scalar(
        select(CurrencyModel).where(CurrencyModel.code == currency_code)
    )
    if currency is None or not currency.is_active:
        raise ValueError("The returned quote currency must already be active in reference data")

    venue = await session.scalar(
        select(TradingVenueModel).where(TradingVenueModel.mic == FRANKFURT_MIC)
    )
    create_venue = venue is None
    if venue is not None and (
        not venue.is_active or venue.country_code != "DE" or venue.timezone != "Europe/Berlin"
    ):
        raise ValueError("Existing XFRA reference data is inactive or inconsistent; review it")
    if venue is None:
        # Verified operating MIC, not a guessed product segment. See docs/frankfurt-quotes.md.
        venue = TradingVenueModel(
            id=uuid4(),
            mic=FRANKFURT_MIC,
            name="Frankfurter Wertpapierbörse",
            country_code="DE",
            timezone="Europe/Berlin",
            is_active=True,
            reference_version="DB-XFRA-20260912",
            version=1,
            created_at=retrieved_at,
            updated_at=retrieved_at,
        )

    listings = list(
        await session.scalars(
            select(WarrantListingModel).where(
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.warrant_id == warrant_id,
                WarrantListingModel.trading_venue_id == venue.id,
            )
        )
    )
    active = [
        row
        for row in listings
        if row.lifecycle_status == WarrantLifecycle.ACTIVE
        and row.quotation_currency_code == currency_code
    ]
    if len(active) > 1 or (not active and listings):
        raise ValueError(
            "Existing Frankfurt listings are ambiguous, inactive or use another currency"
        )
    create_listing = not active
    listing = (
        active[0]
        if active
        else WarrantListingModel(
            id=uuid4(),
            workspace_id=workspace_id,
            warrant_id=warrant_id,
            trading_venue_id=venue.id,
            symbol=None,
            quotation_currency_code=currency_code,
            lifecycle_status=WarrantLifecycle.ACTIVE,
            version=1,
            created_at=retrieved_at,
            updated_at=retrieved_at,
        )
    )
    mappings = list(
        await session.scalars(
            select(WarrantProviderMappingModel).where(
                WarrantProviderMappingModel.provider == PROVIDER,
                or_(
                    WarrantProviderMappingModel.warrant_listing_id == listing.id,
                    (WarrantProviderMappingModel.provider_symbol == warrant.isin)
                    & (WarrantProviderMappingModel.provider_exchange_code == PUBLIC_EXCHANGE_CODE),
                ),
            )
        )
    )
    if len(mappings) > 1:
        raise ValueError("Conflicting Frankfurt mappings; no data changed")
    mapping = mappings[0] if mappings else None
    if mapping is not None and (
        mapping.workspace_id != workspace_id
        or mapping.warrant_listing_id != listing.id
        or mapping.provider_symbol != warrant.isin
        or mapping.provider_exchange_code != PUBLIC_EXCHANGE_CODE
        or mapping.status != MappingStatus.ACTIVE
        or mapping.validated_at is None
    ):
        raise ValueError(
            "Existing Frankfurt mapping conflicts with verified identity; no data changed"
        )
    create_mapping = mapping is None
    if mapping is None:
        mapping = WarrantProviderMappingModel(
            id=uuid4(),
            workspace_id=workspace_id,
            warrant_listing_id=listing.id,
            provider=PROVIDER,
            provider_symbol=warrant.isin,
            provider_exchange_code=PUBLIC_EXCHANGE_CODE,
            status=MappingStatus.ACTIVE,
            validated_at=retrieved_at,
            validation_message=(
                "Official public REST response verified exact ISIN/XSC/currency; "
                "indicative reference only; WKN not returned; delay unknown"
            ),
            version=1,
            created_at=retrieved_at,
            updated_at=retrieved_at,
        )
    if apply:
        if create_venue:
            session.add(venue)
            await session.flush()
        if create_listing:
            session.add(listing)
            await session.flush()
        if create_mapping:
            await SqlAlchemyWarrantProviderMappingRepository(session).add(mapping)
        await session.commit()
    return {
        "status": "APPLIED" if apply else "DRY_RUN",
        "workspace_id": workspace_id,
        "warrant_id": warrant_id,
        "isin": warrant.isin,
        "currency": currency_code,
        "venue_mic": FRANKFURT_MIC,
        "provider": PROVIDER,
        "provider_identity": warrant.isin,
        "provider_exchange_code": PUBLIC_EXCHANGE_CODE,
        "warrant_listing_id": listing.id,
        "mapping_id": mapping.id,
        "create_venue": create_venue,
        "create_listing": create_listing,
        "create_mapping": create_mapping,
        "observation": observation.model_dump(mode="json"),
        "analysis_usable": True,
        "execution_usable": False,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            return await configure_warrant(
                session,
                FrankfurtSnapshotClient(settings.market_data.frankfurt),
                workspace_id=args.workspace_id,
                warrant_id=args.warrant_id,
                apply=args.apply,
            )
    finally:
        await database.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warrant-id", required=True, type=UUID)
    parser.add_argument("--workspace-id", type=UUID, default=DEFAULT_WORKSPACE)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the verified setup in one transaction",
    )
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except (ValueError, FrankfurtSourceError) as exc:
        parser.exit(1, f"Frankfurt setup: {exc}\n")
    print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
