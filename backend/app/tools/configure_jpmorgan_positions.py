"""Preview/hash-checked installation of seven evidenced issuer routes.

No trade, quantity, cash, lifecycle or existing selected source is modified.
The issuer route is attached to a deterministic existing EUR listing; it does
not assert that the quote originates at that listing's exchange.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.providers.jpmorgan.adapter import parse_item
from app.providers.jpmorgan.products import EVIDENCE, INSTRUMENTS
from app.providers.jpmorgan.stream import StreamItem, fetch_batch

WORKSPACE = UUID("00000000-0000-4000-8000-000000000001")
PROVIDER = MarketDataProvider.JPMORGAN


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def plan(session: AsyncSession, workspace: UUID) -> dict[str, Any]:
    positions = (
        await session.execute(
            select(PositionModel, TradeModel, WarrantModel)
            .join(TradeModel, TradeModel.id == PositionModel.trade_id)
            .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
            .where(
                TradeModel.workspace_id == workspace,
                WarrantModel.workspace_id == workspace,
                TradeModel.product_id == WarrantModel.id,
                TradeModel.cancelled_at.is_(None),
                PositionModel.open_quantity > 0,
                PositionModel.closed_at.is_(None),
                WarrantModel.lifecycle_status == "ACTIVE",
                WarrantModel.isin.in_(INSTRUMENTS),
            )
            .order_by(WarrantModel.isin, PositionModel.id)
        )
    ).all()
    eligible, excluded = [], []
    for position, trade, warrant in positions:
        active = list(
            await session.scalars(
                select(PositionQuoteSourceSelectionModel).where(
                    PositionQuoteSourceSelectionModel.workspace_id == workspace,
                    PositionQuoteSourceSelectionModel.position_id == position.id,
                    PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                )
            )
        )
        reason = None
        if warrant.wkn is not None and warrant.wkn != warrant.isin[5:11]:
            reason = "WKN_IDENTITY_CONFLICT"
        if len(active) != 1 or active[0].selection_status != "NO_VERIFIED_QUOTE_SOURCE":
            reason = "EXISTING_SELECTION_PRESERVED"
        listings = (
            await session.execute(
                select(WarrantListingModel, TradingVenueModel)
                .join(
                    TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id
                )
                .join(
                    CurrencyModel, CurrencyModel.code == WarrantListingModel.quotation_currency_code
                )
                .where(
                    WarrantListingModel.workspace_id == workspace,
                    WarrantListingModel.warrant_id == warrant.id,
                    WarrantListingModel.lifecycle_status == "ACTIVE",
                    WarrantListingModel.quotation_currency_code == "EUR",
                    TradingVenueModel.is_active.is_(True),
                    CurrencyModel.is_active.is_(True),
                )
                .order_by(WarrantListingModel.id)
            )
        ).all()
        # Existing issuer mappings are respected, never moved to another listing.
        mappings = list(
            await session.scalars(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.provider == PROVIDER,
                    WarrantProviderMappingModel.provider_symbol == warrant.isin,
                )
            )
        )
        if not listings:
            reason = reason or "ACTIVE_EUR_LISTING_REQUIRED"
        chosen = listings[0] if listings else None
        if mappings:
            if len(mappings) == 1:
                chosen = next(
                    (row for row in listings if row[0].id == mappings[0].warrant_listing_id), None
                )
            if (
                len(mappings) != 1
                or chosen is None
                or verified_identity(
                    workspace, chosen[0], warrant, chosen[1], PROVIDER, mappings[0]
                )
                is None
            ):
                reason = reason or "MAPPING_CONFLICT"
        if reason:
            excluded.append(
                {"position_id": str(position.id), "isin": warrant.isin, "reason": reason}
            )
            continue
        assert chosen is not None  # All missing/conflicting routes were excluded above.
        listing, venue = chosen
        eligible.append(
            {
                "position_id": str(position.id),
                "open_quantity": position.open_quantity,
                "cost_basis": str(position.cost_basis),
                "last_execution_at": position.last_execution_at.isoformat(),
                "trade_id": str(trade.id),
                "trade_origin": trade.origin,
                "product_evaluation_id": (
                    str(trade.product_evaluation_id) if trade.product_evaluation_id else None
                ),
                "warrant_id": str(warrant.id),
                "warrant_version": warrant.version,
                "isin": warrant.isin,
                "wkn": warrant.wkn,
                "listing_id": str(listing.id),
                "listing_version": listing.version,
                "listing_mic": venue.mic,
                "venue_version": venue.version,
                "currency": "EUR",
                "provider_exchange_code": "ISSUER",
                "instrument_id": INSTRUMENTS[warrant.isin],
                "previous_selection_id": str(active[0].id),
                "previous_selection_reason": active[0].selection_reason,
                "mapping_id": str(mappings[0].id) if mappings else None,
                "mapping_version": mappings[0].version if mappings else None,
            }
        )
    payload = {
        "workspace_id": str(workspace),
        "provider": PROVIDER.value,
        "evidence": EVIDENCE,
        "eligible": eligible,
        "excluded": excluded,
    }
    return {**payload, "preview_sha256": digest(payload), "eligible_count": len(eligible)}


async def apply_plan(
    database: DatabaseManager, workspace: UUID, expected: str, batch: dict[str, StreamItem]
) -> dict[str, Any]:
    async with database.session_context() as session:
        # Protect the re-read against concurrent selection/listing/master-data writes.
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        preview = await plan(session, workspace)
        if preview["preview_sha256"] != expected:
            raise ValueError("JPMORGAN_PREVIEW_CHANGED")
        now = datetime.now(UTC)
        selection_ids = []
        for item in preview["eligible"]:
            isin = item["isin"]
            snapshot = batch.get(isin)
            if snapshot is None:
                raise ValueError("JPMORGAN_REQUIRED_SNAPSHOT_MISSING")
            request = WarrantQuoteRequest(
                workspace, UUID(item["listing_id"]), uuid4(), now, expected_currency="EUR"
            )
            quote = parse_item(
                snapshot, request, SimpleNamespace(isin=isin, wkn=item["wkn"], currency="EUR")
            )
            if quote.bid is None:
                raise ValueError("JPMORGAN_INDICATIVE_BID_REQUIRED")
            mapping = await session.scalar(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.provider == PROVIDER,
                    WarrantProviderMappingModel.provider_symbol == isin,
                )
            )
            if mapping is None:
                mapping = WarrantProviderMappingModel(
                    id=uuid4(),
                    workspace_id=workspace,
                    warrant_listing_id=request.warrant_listing_id,
                    provider=PROVIDER,
                    provider_symbol=isin,
                    provider_exchange_code="ISSUER",
                    status=MappingStatus.ACTIVE,
                    validated_at=now,
                    validation_message=EVIDENCE,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(mapping)
                await session.flush()
            listing = await session.get(WarrantListingModel, request.warrant_listing_id)
            warrant = await session.get(WarrantModel, UUID(item["warrant_id"]))
            if listing is None or warrant is None:
                raise ValueError("ISSUER_IDENTITY_CHANGED")
            venue = await session.get(TradingVenueModel, listing.trading_venue_id)
            if venue is None:
                raise ValueError("ISSUER_IDENTITY_CHANGED")
            identity = verified_identity(workspace, listing, warrant, venue, PROVIDER, mapping)
            if identity is None:
                raise ValueError("JPMORGAN_IDENTITY_CHANGED")
            initial_result = MarketDataResult(
                data=quote,
                provider=PROVIDER,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                correlation_id=request.correlation_id,
                retrieved_at=snapshot.received_at,
                cache_status=CacheStatus.MISS,
                quality_status=QualityStatus.VALID,
                warnings=("QUOTE_DATE_AND_TIMEZONE_UNKNOWN", "ISSUER_INDICATION_NOT_EXECUTABLE"),
                retry_count=0,
                provider_call_cost=0,
                reason_code="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
            )
            payload = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None]).dump_python(
                initial_result, mode="json"
            )
            observation = await session.get(
                WarrantQuoteObservationModel, (workspace, listing.id, PROVIDER.value)
            )
            if observation is None:
                session.add(
                    WarrantQuoteObservationModel(
                        workspace_id=workspace,
                        warrant_listing_id=listing.id,
                        provider=PROVIDER.value,
                        identity_key=identity.key,
                        payload=payload,
                    )
                )
            else:
                observation.identity_key, observation.payload = identity.key, payload
            old = await session.get(
                PositionQuoteSourceSelectionModel, UUID(item["previous_selection_id"])
            )
            if (
                old is None
                or old.superseded_at is not None
                or old.selection_status != "NO_VERIFIED_QUOTE_SOURCE"
            ):
                raise ValueError("JPMORGAN_SELECTION_CHANGED")
            old.superseded_at = now
            await session.flush()
            selection_id = uuid4()
            session.add(
                PositionQuoteSourceSelectionModel(
                    id=selection_id,
                    workspace_id=workspace,
                    position_id=UUID(item["position_id"]),
                    warrant_listing_id=listing.id,
                    warrant_provider_mapping_id=mapping.id,
                    provider=PROVIDER.value,
                    identity_key=identity.key,
                    mapping_version=mapping.version,
                    selection_status="SELECTED",
                    selection_reason="VERIFIED_JPMORGAN_ISSUER_INDICATION",
                    policy_version="JPMORGAN_ISSUER_INDICATION_V1",
                    selected_at=now,
                    evidence={
                        "product_identity": EVIDENCE,
                        "instrument_id": INSTRUMENTS[isin],
                        "quote_time_basis": "DATE_AND_TIMEZONE_UNKNOWN",
                        "execution_usable": False,
                        "preview_sha256": expected,
                        "previous_selection_id": str(old.id),
                    },
                )
            )
            selection_ids.append(str(selection_id))
        await session.commit()
        return {
            "applied": True,
            "reselected": len(selection_ids),
            "selection_ids": selection_ids,
            "preview_sha256": expected,
        }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    database = DatabaseManager(settings)
    try:
        if args.apply:
            if not settings.market_data.jpmorgan.enabled:
                raise ValueError("JPMORGAN_MUST_BE_ENABLED")
            if not args.expected_preview_sha256:
                raise ValueError("JPMORGAN_PREVIEW_HASH_REQUIRED")
            async with database.session_context() as session:
                current = await plan(session, args.workspace_id)
            if current["preview_sha256"] != args.expected_preview_sha256:
                raise ValueError("JPMORGAN_PREVIEW_CHANGED")
            if current["eligible_count"] == 0:
                return {
                    "applied": True,
                    "reselected": 0,
                    "selection_ids": [],
                    "preview_sha256": current["preview_sha256"],
                }
            # Network outside the write transaction. Snapshot date is never manufactured.
            batch = await fetch_batch(settings.market_data.jpmorgan.timeout_seconds)
            return await apply_plan(
                database, args.workspace_id, args.expected_preview_sha256, batch
            )
        async with database.session_context() as session:
            return {"applied": False, **await plan(session, args.workspace_id)}
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=UUID, default=WORKSPACE)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-preview-sha256")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
