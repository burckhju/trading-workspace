"""Preview or repair GETTEX mappings bound to a non-GETTEX warrant listing."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
_GETTEX_MICS = {"MUND", "MUNC"}


async def _repair_session(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    apply: bool,
) -> dict[str, object]:
    statement = (
        select(
            WarrantProviderMappingModel,
            WarrantListingModel,
            WarrantModel,
            TradingVenueModel,
        )
        .join(
            WarrantListingModel,
            WarrantListingModel.id == WarrantProviderMappingModel.warrant_listing_id,
        )
        .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
        .join(
            TradingVenueModel,
            TradingVenueModel.id == WarrantListingModel.trading_venue_id,
        )
        .where(
            WarrantProviderMappingModel.workspace_id == workspace_id,
            WarrantProviderMappingModel.provider == MarketDataProvider.GETTEX_DELAYED,
            WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
            WarrantProviderMappingModel.validated_at.is_not(None),
        )
        .order_by(WarrantModel.isin, WarrantProviderMappingModel.id)
    )
    if apply:
        statement = statement.with_for_update()
    rows = (await session.execute(statement)).all()

    plans: list[dict[str, object]] = []
    changed = 0
    for mapping, source_listing, warrant, source_venue in rows:
        target_mic = mapping.provider_exchange_code
        if target_mic not in _GETTEX_MICS:
            raise ValueError(f"GETTEX_MAPPING_EXCHANGE_INVALID_{target_mic}")
        if mapping.provider_symbol != warrant.isin:
            raise ValueError("GETTEX_MAPPING_ISIN_MISMATCH")

        selections = list(
            await session.scalars(
                select(PositionQuoteSourceSelectionModel.id).where(
                    PositionQuoteSourceSelectionModel.workspace_id == workspace_id,
                    PositionQuoteSourceSelectionModel.warrant_provider_mapping_id == mapping.id,
                    PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                )
            )
        )
        if selections:
            raise ValueError(f"GETTEX_MAPPING_HAS_ACTIVE_POSITION_SELECTION_{mapping.id}")

        observation_count = len(
            list(
                await session.scalars(
                    select(WarrantQuoteObservationModel.warrant_listing_id).where(
                        WarrantQuoteObservationModel.workspace_id == workspace_id,
                        WarrantQuoteObservationModel.warrant_listing_id == source_listing.id,
                        WarrantQuoteObservationModel.provider
                        == MarketDataProvider.GETTEX_DELAYED.value,
                    )
                )
            )
        )

        if source_venue.mic == target_mic:
            plans.append(
                {
                    "isin": warrant.isin,
                    "mapping_id": str(mapping.id),
                    "action": "ALREADY_CORRECT",
                    "source_listing_id": str(source_listing.id),
                    "source_mic": source_venue.mic,
                    "target_listing_id": str(source_listing.id),
                    "target_mic": target_mic,
                    "old_observations_left_in_place": observation_count,
                }
            )
            continue

        target_venue = await session.scalar(
            select(TradingVenueModel).where(
                TradingVenueModel.mic == target_mic,
                TradingVenueModel.is_active.is_(True),
            )
        )
        if target_venue is None:
            raise ValueError(f"GETTEX_TARGET_VENUE_NOT_FOUND_{target_mic}")

        target_listings = list(
            await session.scalars(
                select(WarrantListingModel)
                .where(
                    WarrantListingModel.workspace_id == workspace_id,
                    WarrantListingModel.warrant_id == warrant.id,
                    WarrantListingModel.trading_venue_id == target_venue.id,
                )
                .order_by(WarrantListingModel.id)
            )
        )
        if len(target_listings) > 1:
            raise ValueError(f"GETTEX_TARGET_LISTING_CONFLICT_{warrant.isin}_{target_mic}")

        now = datetime.now(UTC)
        action = "MOVE_MAPPING_TO_EXISTING_LISTING"
        if target_listings:
            target_listing = target_listings[0]
            if target_listing.lifecycle_status != WarrantLifecycle.ACTIVE:
                raise ValueError(f"GETTEX_TARGET_LISTING_INACTIVE_{warrant.isin}_{target_mic}")
            if target_listing.quotation_currency_code != source_listing.quotation_currency_code:
                raise ValueError(
                    f"GETTEX_TARGET_LISTING_CURRENCY_MISMATCH_{warrant.isin}_{target_mic}"
                )
        else:
            action = "CREATE_LISTING_AND_MOVE_MAPPING"
            target_listing = WarrantListingModel(
                id=uuid4(),
                workspace_id=workspace_id,
                warrant_id=warrant.id,
                trading_venue_id=target_venue.id,
                symbol=None,
                quotation_currency_code=source_listing.quotation_currency_code,
                lifecycle_status=WarrantLifecycle.ACTIVE,
                version=1,
                created_at=now,
                updated_at=now,
            )
            if apply:
                session.add(target_listing)
                await session.flush()

        plans.append(
            {
                "isin": warrant.isin,
                "mapping_id": str(mapping.id),
                "action": action,
                "source_listing_id": str(source_listing.id),
                "source_mic": source_venue.mic,
                "target_listing_id": str(target_listing.id) if apply or target_listings else None,
                "target_mic": target_mic,
                "mapping_version_before": mapping.version,
                "mapping_version_after": mapping.version + 1,
                "old_observations_left_in_place": observation_count,
            }
        )
        changed += 1

        if apply:
            mapping.warrant_listing_id = target_listing.id
            mapping.version += 1
            mapping.updated_at = now
            mapping.validation_message = (
                "Venue-corrected GETTEX route; exact operator-confirmed "
                f"ISIN/{target_mic} evidence retained; prior observations remain "
                "on the historical listing"
            )
            await session.flush()

    return {
        "applied": apply,
        "workspace_id": str(workspace_id),
        "provider": MarketDataProvider.GETTEX_DELAYED.value,
        "mapping_count": len(rows),
        "changed_count": changed,
        "plans": plans,
    }


async def repair(*, apply: bool, confirmation: bool) -> dict[str, object]:
    settings = get_settings()
    if apply and (
        not settings.market_data.gettex_delayed.enabled
        or not settings.market_data.gettex_delayed.private_use_confirmed
    ):
        raise ValueError("GETTEX_PROVIDER_MUST_BE_ENABLED_WITH_PRIVATE_USE_CONFIRMATION")
    if apply and settings.market_data.refresh.enabled:
        raise ValueError("MARKET_DATA_REFRESH_MUST_BE_DISABLED")
    if apply and settings.market_data.refresh.auto_configure:
        raise ValueError("MARKET_DATA_AUTO_CONFIGURE_MUST_BE_DISABLED")
    if apply and not confirmation:
        raise ValueError("GETTEX_ROUTE_REPAIR_CONFIRMATION_REQUIRED")

    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            result = await _repair_session(
                session,
                workspace_id=WORKSPACE_ID,
                apply=apply,
            )
            if apply:
                await session.commit()
            return result
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-route-repair", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        repair(
            apply=args.apply,
            confirmation=args.confirm_route_repair,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
