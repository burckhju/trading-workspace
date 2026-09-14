"""Explicit same-currency primary-listing change after catalog and EOD verification.

Dry-run by default. Instruments are supplied by the operator, never seeded by a
migration. The scheduler does not invoke this command or choose another venue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.di import ApplicationContainer
from app.features.market.domain.enums import LifecycleStatus
from app.features.market.domain.normalization import normalize_isin
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market.service.listing_service import ListingService
from app.features.market.service.types import Actor, AddListing, SetPrimaryListing
from app.features.market.service.unit_of_work import SqlAlchemyMarketUnitOfWork
from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.persistence.mapping import (
    daily_price_to_domain,
    mapping_to_domain,
)
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.service.catalog_mapping_validation import (
    CatalogMappingResolver,
)
from app.features.market_data.service.refresh_discovery import discover_underlying
from app.features.market_data.service.types import DailyPriceRequest
from app.providers.eodhd.stock_catalog import StockCatalogIdentity

ACTOR = Actor(None, "Explicit verified underlying venue switch")


class VenueSwitchError(ValueError):
    """Safe operational reason code, without transport details or secrets."""


@dataclass(frozen=True)
class SwitchPlan:
    workspace_id: UUID
    underlying_id: UUID
    isin: str
    name: str
    source_id: UUID
    source_version: int
    source_mic: str
    target_venue_id: UUID
    target_id: UUID | None
    target_version: int | None
    currency: str
    identity: StockCatalogIdentity

    def summary(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "underlying_id": self.underlying_id,
            "isin": self.isin,
            "name": self.name,
            "previous_primary_listing_id": self.source_id,
            "previous_mic": self.source_mic,
            "target_listing_id": self.target_id,
            "target_mic": self.identity.mic,
            "currency": self.currency,
            "provider": "EODHD",
            "provider_identity": self.identity.item.provider_symbol,
            "provider_exchange_code": self.identity.item.provider_exchange_code,
            "catalog_endpoint": self.identity.endpoint,
            "catalog_retrieved_at": self.identity.catalog_retrieved_at,
            "execution_usable": False,
        }


async def prepare(
    container: ApplicationContainer,
    *,
    workspace_id: UUID,
    isin: str,
    from_mic: str,
    to_mic: str,
    currency: str,
) -> SwitchPlan:
    """Read-only proposal; only exact current master data and target proof qualify."""
    if normalize_isin(isin) != isin:
        raise VenueSwitchError("CANONICAL_ISIN_REQUIRED")
    adapter = container.require_eodhd_adapter()
    async with container.database.session_context() as session:
        underlying = await session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.isin == isin,
                UnderlyingModel.lifecycle_status == LifecycleStatus.ACTIVE,
            )
        )
        if underlying is None:
            raise VenueSwitchError("ACTIVE_UNDERLYING_NOT_FOUND")
        listings = list(
            await session.scalars(
                select(ListingModel).where(
                    ListingModel.workspace_id == workspace_id,
                    ListingModel.underlying_id == underlying.id,
                )
            )
        )
        primaries = [row for row in listings if row.is_primary]
        if len(primaries) != 1 or primaries[0].lifecycle_status != LifecycleStatus.ACTIVE:
            raise VenueSwitchError("ONE_ACTIVE_PRIMARY_LISTING_REQUIRED")
        source = primaries[0]
        source_venue = await session.get(TradingVenueModel, source.trading_venue_id)
        if source_venue is None or source_venue.mic not in {from_mic, to_mic}:
            raise VenueSwitchError("PRIMARY_VENUE_CHANGED")
        if source.currency_code != currency:
            raise VenueSwitchError("RULE_CURRENCY_CHANGE_NOT_ALLOWED")
        target_venue = await session.scalar(
            select(TradingVenueModel).where(
                TradingVenueModel.mic == to_mic,
                TradingVenueModel.is_active.is_(True),
            )
        )
        if target_venue is None:
            raise VenueSwitchError("ACTIVE_TARGET_VENUE_REQUIRED")
        currency_row = await session.get(CurrencyModel, currency)
        if currency_row is None or not currency_row.is_active:
            raise VenueSwitchError("ACTIVE_CURRENCY_REQUIRED")
        discovery = await adapter.stock_catalog.discover_with_search(
            isin=isin,
            currency=currency,
            mic=to_mic,
        )
        proof = discovery.identity
        if proof is None:
            raise VenueSwitchError(discovery.reason)
        if (proof.item.isin, proof.item.currency, proof.mic) != (
            isin,
            currency,
            to_mic,
        ):
            raise VenueSwitchError("CATALOG_IDENTITY_MISMATCH")
        targets = [row for row in listings if row.trading_venue_id == target_venue.id]
        if len(targets) > 1:
            raise VenueSwitchError("TARGET_LISTING_AMBIGUOUS")
        target = targets[0] if targets else None
        if target is not None and (
            target.currency_code != currency
            or target.ticker != proof.item.provider_symbol
            or target.lifecycle_status != LifecycleStatus.ACTIVE
        ):
            raise VenueSwitchError("EXISTING_TARGET_LISTING_CONFLICT")
        if target is not None:
            mapping = await session.scalar(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == workspace_id,
                    ProviderInstrumentMappingModel.listing_id == target.id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                )
            )
            if mapping is not None:
                await verify_mapping(session, workspace_id, target.id, proof, mapping)
        return SwitchPlan(
            workspace_id,
            underlying.id,
            isin,
            underlying.name,
            source.id,
            source.version,
            source_venue.mic,
            target_venue.id,
            target.id if target else None,
            target.version if target else None,
            currency,
            proof,
        )


async def verify_mapping(
    session: AsyncSession,
    workspace_id: UUID,
    listing_id: UUID,
    proof: StockCatalogIdentity,
    mapping: ProviderInstrumentMappingModel | None,
) -> ProviderInstrumentMappingModel:
    if mapping is None or mapping.status != MappingStatus.ACTIVE or mapping.validated_at is None:
        raise VenueSwitchError("VALIDATED_TARGET_MAPPING_REQUIRED")
    check = await CatalogMappingResolver(session, workspace_id, listing_id, proof).validate_mapping(
        mapping_to_domain(mapping)
    )
    if check.status != MappingStatus.ACTIVE:
        raise VenueSwitchError("TARGET_MAPPING_IDENTITY_CONFLICT")
    return mapping


async def check_source(session: AsyncSession, plan: SwitchPlan) -> None:
    underlying = await session.get(UnderlyingModel, plan.underlying_id, with_for_update=True)
    if (
        underlying is None
        or underlying.workspace_id != plan.workspace_id
        or underlying.isin != plan.isin
        or underlying.lifecycle_status != LifecycleStatus.ACTIVE
    ):
        raise VenueSwitchError("UNDERLYING_CHANGED_DURING_VERIFICATION")
    rows = list(
        await session.scalars(
            select(ListingModel)
            .where(
                ListingModel.workspace_id == plan.workspace_id,
                ListingModel.underlying_id == plan.underlying_id,
            )
            .with_for_update()
        )
    )
    primaries = [row for row in rows if row.is_primary]
    if (
        len(primaries) != 1
        or primaries[0].id != plan.source_id
        or primaries[0].version != plan.source_version
        or primaries[0].currency_code != plan.currency
        or primaries[0].lifecycle_status != LifecycleStatus.ACTIVE
    ):
        raise VenueSwitchError("PRIMARY_CHANGED_DURING_VERIFICATION")


async def apply_plan(container: ApplicationContainer, plan: SwitchPlan) -> dict[str, Any]:
    """Stage non-primary data first; primary flags change only after a valid EOD import."""
    target_id, target_version = plan.target_id, plan.target_version
    if target_id is None:
        async with container.database.session_context() as session:
            await check_source(session, plan)
            created_target = await ListingService(SqlAlchemyMarketUnitOfWork(session)).add(
                AddListing(
                    plan.workspace_id,
                    plan.underlying_id,
                    ACTOR,
                    plan.target_venue_id,
                    plan.identity.item.provider_symbol,
                    plan.currency,
                    is_primary=False,
                )
            )
            target_id, target_version = created_target.id, created_target.version
    discovery = await discover_underlying(container, plan.workspace_id, target_id)
    if discovery["status"] != "AVAILABLE":
        raise VenueSwitchError(str(discovery["reason"]))
    async with container.database.session_context() as session:
        mapping = await verify_mapping(
            session,
            plan.workspace_id,
            target_id,
            plan.identity,
            await session.scalar(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == plan.workspace_id,
                    ProviderInstrumentMappingModel.listing_id == target_id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                )
            ),
        )
        mapping_id, mapping_version = mapping.id, mapping.version
    now = datetime.now(UTC)
    end = now.date() - timedelta(days=1)
    async with container.daily_price_import_service() as importer:
        imported = await importer.import_daily_prices(
            DailyPriceRequest(
                plan.workspace_id,
                target_id,
                mapping_id,
                end - timedelta(days=400),
                end,
                uuid4(),
            )
        )
    if (
        not imported.processed
        or imported.quality_status != QualityStatus.VALID
        or imported.provider != MarketDataProvider.EODHD
    ):
        raise VenueSwitchError("VALID_COMPLETED_EOD_IMPORT_REQUIRED")
    async with container.database.session_context() as session:
        await check_source(session, plan)
        target = await session.get(ListingModel, target_id)
        if target is None or target.version != target_version:
            raise VenueSwitchError("TARGET_CHANGED_DURING_VERIFICATION")
        mapping = await verify_mapping(
            session,
            plan.workspace_id,
            target_id,
            plan.identity,
            await session.get(ProviderInstrumentMappingModel, mapping_id, with_for_update=True),
        )
        if mapping.version != mapping_version:
            raise VenueSwitchError("MAPPING_CHANGED_DURING_VERIFICATION")
        price = await session.scalar(
            select(DailyPriceModel)
            .where(
                DailyPriceModel.workspace_id == plan.workspace_id,
                DailyPriceModel.listing_id == target_id,
            )
            .order_by(DailyPriceModel.trading_date.desc())
            .limit(1)
        )
        if price is None:
            raise VenueSwitchError("PERSISTED_EOD_REQUIRED")
        # Reconstruct the domain model to check OHLC, finite prices and currency too.
        daily = daily_price_to_domain(price)
        age = (datetime.now(UTC).date() - daily.trading_date).days
        if (
            daily.quality_status != QualityStatus.VALID
            or daily.currency != plan.currency
            or daily.provider != MarketDataProvider.EODHD
            or daily.provider_symbol != plan.identity.item.provider_symbol
            or daily.retrieved_at != imported.retrieved_at
            or not 1 <= age <= container.settings.position_monitoring.max_completed_price_age_days
        ):
            raise VenueSwitchError("RECENT_MATCHING_COMPLETED_EOD_REQUIRED")
        changed = not target.is_primary
        if changed:
            await ListingService(SqlAlchemyMarketUnitOfWork(session)).set_primary(
                SetPrimaryListing(
                    plan.workspace_id,
                    plan.underlying_id,
                    target_id,
                    target.version,
                    ACTOR,
                )
            )
        return {
            **plan.summary(),
            "status": "APPLIED" if changed else "ALREADY_PRIMARY",
            "target_listing_id": target_id,
            "mapping_id": mapping_id,
            "primary_changed": changed,
            "data_verified": True,
            "trading_date": daily.trading_date,
            "close": daily.close,
            "low": daily.low,
            "high": daily.high,
            "retrieved_at": daily.retrieved_at,
            "processed": imported.processed,
            "max_completed_price_age_days": (
                container.settings.position_monitoring.max_completed_price_age_days
            ),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--isin", action="append", required=True)
    parser.add_argument("--from-mic", required=True)
    parser.add_argument("--to-mic", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser


async def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    # Validate the entire explicit selection before connecting or writing anything.
    isins = list(dict.fromkeys(normalize_isin(value) for value in args.isin))
    if not 1 <= len(isins) <= 100 or None in isins:
        raise VenueSwitchError("ONE_TO_100_EXPLICIT_ISINS_REQUIRED")
    from_mic, to_mic, currency = (
        args.from_mic.upper(),
        args.to_mic.upper(),
        args.currency.upper(),
    )
    if (
        not re.fullmatch(r"[A-Z0-9]{4}", from_mic)
        or not re.fullmatch(r"[A-Z0-9]{4}", to_mic)
        or not re.fullmatch(r"[A-Z]{3}", currency)
        or from_mic == to_mic
    ):
        raise VenueSwitchError("EXPLICIT_SOURCE_TARGET_AND_CURRENCY_REQUIRED")
    container = ApplicationContainer.build(get_settings())
    results: list[dict[str, Any]] = []
    try:
        container.require_eodhd_adapter()
        await container.synchronize_eodhd_account_usage()
        for index, isin in enumerate(isins):
            assert isin is not None
            if index:
                await asyncio.sleep(container.settings.market_data.refresh.request_spacing_seconds)
            try:
                plan = await prepare(
                    container,
                    workspace_id=args.workspace_id,
                    isin=isin,
                    from_mic=from_mic,
                    to_mic=to_mic,
                    currency=currency,
                )
                result = (
                    await apply_plan(container, plan)
                    if args.apply
                    else {
                        **plan.summary(),
                        "status": "DRY_RUN",
                        "data_verified": False,
                    }
                )
            except Exception as exc:
                result = {
                    "isin": isin,
                    "status": "BLOCKED",
                    "reason": (
                        str(exc) if isinstance(exc, VenueSwitchError) else type(exc).__name__
                    ),
                }
            results.append(result)
        return results
    finally:
        await container.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        results = asyncio.run(run(args))
    except Exception as exc:
        parser.exit(1, f"Venue switch: {type(exc).__name__}\n")
    print(json.dumps(results, default=str, ensure_ascii=False, indent=2))
    return int(any(row["status"] == "BLOCKED" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
