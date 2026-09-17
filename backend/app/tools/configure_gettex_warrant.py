"""Preview or create one explicit gettex MUND/MUNC warrant mapping."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def configure(*, isin: str, mic: str, apply: bool, evidence_confirmed: bool) -> dict[str, object]:
    settings = get_settings()
    normalized_isin = isin.strip().upper()
    normalized_mic = mic.strip().upper()
    if normalized_mic not in {"MUND", "MUNC"}:
        raise ValueError("GETTEX_MIC_MUST_BE_MUND_OR_MUNC")
    if len(normalized_isin) != 12 or not normalized_isin.isalnum():
        raise ValueError("GETTEX_ISIN_INVALID")
    if apply and (
        not settings.market_data.gettex_delayed.enabled
        or not settings.market_data.gettex_delayed.private_use_confirmed
    ):
        raise ValueError("GETTEX_PROVIDER_MUST_BE_ENABLED_WITH_PRIVATE_USE_CONFIRMATION")
    if apply and not evidence_confirmed:
        raise ValueError("GETTEX_EXACT_INSTRUMENT_EVIDENCE_CONFIRMATION_REQUIRED")

    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            warrants = list(
                await session.scalars(
                    select(WarrantModel).where(
                        WarrantModel.workspace_id == WORKSPACE_ID,
                        WarrantModel.isin == normalized_isin,
                        WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    )
                )
            )
            if len(warrants) != 1:
                raise ValueError(f"GETTEX_ACTIVE_WARRANT_COUNT_{len(warrants)}")
            warrant = warrants[0]
            listings = list(
                await session.scalars(
                    select(WarrantListingModel)
                    .join(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .where(
                        WarrantListingModel.workspace_id == WORKSPACE_ID,
                        WarrantListingModel.warrant_id == warrant.id,
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        TradingVenueModel.is_active.is_(True),
                    )
                    .order_by(WarrantListingModel.id)
                )
            )
            if len(listings) != 1:
                raise ValueError(f"GETTEX_ACTIVE_LISTING_COUNT_{len(listings)}")
            listing = listings[0]
            mappings = list(
                await session.scalars(
                    select(WarrantProviderMappingModel).where(
                        WarrantProviderMappingModel.provider == MarketDataProvider.GETTEX_DELAYED,
                        or_(
                            WarrantProviderMappingModel.warrant_listing_id == listing.id,
                            WarrantProviderMappingModel.provider_symbol == normalized_isin,
                        ),
                    )
                )
            )
            if mappings:
                if len(mappings) != 1:
                    raise ValueError("GETTEX_MAPPING_CONFLICT")
                mapping = mappings[0]
                if (
                    mapping.workspace_id != WORKSPACE_ID
                    or mapping.warrant_listing_id != listing.id
                    or mapping.provider_symbol != normalized_isin
                    or mapping.provider_exchange_code != normalized_mic
                ):
                    raise ValueError("GETTEX_MAPPING_CONFLICT")
                if apply and (
                    mapping.status != MappingStatus.ACTIVE or mapping.validated_at is None
                ):
                    now = datetime.now(UTC)
                    mapping.status = MappingStatus.ACTIVE
                    mapping.validated_at = now
                    mapping.validation_message = (
                        "Operator-confirmed exact ISIN/MIC evidence from official gettex delayed "
                        "pre-trade data; indicative/private-use route only"
                    )
                    mapping.updated_at = now
                    mapping.version += 1
                    await session.flush()
                    await session.commit()
                return {
                    "action": "EXISTING_MAPPING",
                    "applied": apply,
                    "isin": normalized_isin,
                    "mic": normalized_mic,
                    "warrant_id": str(warrant.id),
                    "listing_id": str(listing.id),
                    "mapping_id": str(mapping.id),
                    "status": mapping.status.value,
                }

            result: dict[str, object] = {
                "action": "CREATE_MAPPING",
                "applied": apply,
                "isin": normalized_isin,
                "mic": normalized_mic,
                "warrant_id": str(warrant.id),
                "listing_id": str(listing.id),
                "currency": listing.quotation_currency_code,
            }
            if not apply:
                return result
            now = datetime.now(UTC)
            mapping = WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=WORKSPACE_ID,
                warrant_listing_id=listing.id,
                provider=MarketDataProvider.GETTEX_DELAYED,
                provider_symbol=normalized_isin,
                provider_exchange_code=normalized_mic,
                status=MappingStatus.ACTIVE,
                validated_at=now,
                validation_message=(
                    "Operator-confirmed exact ISIN/MIC evidence from official gettex delayed "
                    "pre-trade data; indicative/private-use route only"
                ),
                version=1,
                created_at=now,
                updated_at=now,
            )
            session.add(mapping)
            await session.flush()
            await session.commit()
            return {**result, "mapping_id": str(mapping.id), "status": MappingStatus.ACTIVE.value}
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isin", required=True)
    parser.add_argument("--mic", choices=("MUND", "MUNC"), required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-evidence", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        configure(
            isin=args.isin,
            mic=args.mic,
            apply=args.apply,
            evidence_confirmed=args.confirm_evidence,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
