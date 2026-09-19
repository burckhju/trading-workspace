"""Preview or refresh persisted GETTEX quotes for currently bound open positions."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import and_, select

from app.core.config import get_settings
from app.core.di import ApplicationContainer
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.position_monitoring.service.quote_runtime import (
    build_warrant_quote_resolver,
)
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
_RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])
_MAX_HISTORICAL_EVIDENCE_AGE = timedelta(days=4)


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _binding_payload(row: Any) -> dict[str, object]:
    return {
        "position_id": str(row.position_id),
        "warrant_id": str(row.warrant_id),
        "isin": row.isin,
        "listing_id": str(row.warrant_listing_id),
        "currency": row.quotation_currency_code,
        "provider": row.provider,
        "listing_mic": row.mic,
        "provider_exchange_code": row.provider_exchange_code,
        "persisted_mapping_version": row.persisted_mapping_version,
        "current_mapping_version": row.current_mapping_version,
        "mapping_status": row.mapping_status.value,
        "identity_key": row.identity_key,
    }


def _validate_binding(row: Any) -> None:
    if row.provider != MarketDataProvider.GETTEX_DELAYED.value:
        raise ValueError("BOUND_GETTEX_PROVIDER_CHANGED")
    if row.mic != "MUND" or row.provider_exchange_code != "MUND":
        raise ValueError("BOUND_GETTEX_ROUTE_NOT_MUND")
    if row.mapping_status is not MappingStatus.ACTIVE:
        raise ValueError("BOUND_GETTEX_MAPPING_NOT_ACTIVE")
    if row.persisted_mapping_version != row.current_mapping_version:
        raise ValueError("BOUND_GETTEX_MAPPING_VERSION_CHANGED")
    if not row.identity_key:
        raise ValueError("BOUND_GETTEX_IDENTITY_MISSING")


async def _bindings(container: ApplicationContainer) -> list[Any]:
    async with container.database.session_context() as session:
        rows = (
            await session.execute(
                select(
                    PositionModel.id.label("position_id"),
                    WarrantModel.id.label("warrant_id"),
                    WarrantModel.isin,
                    PositionQuoteSourceSelectionModel.warrant_listing_id,
                    WarrantListingModel.quotation_currency_code,
                    PositionQuoteSourceSelectionModel.provider,
                    TradingVenueModel.mic,
                    WarrantProviderMappingModel.provider_exchange_code,
                    PositionQuoteSourceSelectionModel.mapping_version.label(
                        "persisted_mapping_version"
                    ),
                    WarrantProviderMappingModel.version.label("current_mapping_version"),
                    WarrantProviderMappingModel.status.label("mapping_status"),
                    PositionQuoteSourceSelectionModel.identity_key,
                )
                .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
                .join(
                    PositionQuoteSourceSelectionModel,
                    and_(
                        PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                        PositionQuoteSourceSelectionModel.workspace_id == TradeModel.workspace_id,
                        PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                        PositionQuoteSourceSelectionModel.selection_status == "SELECTED",
                    ),
                )
                .join(
                    WarrantListingModel,
                    WarrantListingModel.id == PositionQuoteSourceSelectionModel.warrant_listing_id,
                )
                .join(
                    TradingVenueModel,
                    TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                )
                .join(
                    WarrantProviderMappingModel,
                    WarrantProviderMappingModel.id
                    == PositionQuoteSourceSelectionModel.warrant_provider_mapping_id,
                )
                .where(
                    TradeModel.workspace_id == WORKSPACE_ID,
                    TradeModel.cancelled_at.is_(None),
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                    PositionQuoteSourceSelectionModel.provider
                    == MarketDataProvider.GETTEX_DELAYED.value,
                )
                .order_by(WarrantModel.isin, PositionModel.id)
            )
        ).all()
        return list(rows)


async def _historical_evidence(
    container: ApplicationContainer,
    warrant_ids: tuple[UUID, ...],
) -> tuple[datetime, dict[str, datetime]]:
    async with container.database.session_context() as session:
        rows = (
            await session.execute(
                select(
                    WarrantModel.id,
                    WarrantModel.isin,
                    WarrantQuoteObservationModel.payload,
                )
                .join(
                    WarrantListingModel,
                    WarrantListingModel.id == WarrantQuoteObservationModel.warrant_listing_id,
                )
                .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                .where(
                    WarrantQuoteObservationModel.workspace_id == WORKSPACE_ID,
                    WarrantQuoteObservationModel.provider
                    == MarketDataProvider.GETTEX_DELAYED.value,
                    WarrantModel.id.in_(warrant_ids),
                )
            )
        ).all()

    latest_by_warrant: dict[UUID, datetime] = {}
    isin_by_warrant: dict[UUID, str] = {}
    for warrant_id, isin, payload in rows:
        try:
            result = _RESULT.validate_python(payload)
        except (ValidationError, ValueError, TypeError):
            continue
        if result.data is None:
            continue
        evidence_at = result.data.observed_at or result.retrieved_at
        previous = latest_by_warrant.get(warrant_id)
        if previous is None or evidence_at > previous:
            latest_by_warrant[warrant_id] = evidence_at
            isin_by_warrant[warrant_id] = isin

    missing = set(warrant_ids) - set(latest_by_warrant)
    if missing:
        raise ValueError(f"BOUND_GETTEX_HISTORICAL_EVIDENCE_MISSING_{len(missing)}")

    as_of = max(latest_by_warrant.values())
    age = datetime.now(UTC) - as_of
    if age < timedelta(0) or age > _MAX_HISTORICAL_EVIDENCE_AGE:
        raise ValueError("BOUND_GETTEX_HISTORICAL_EVIDENCE_TOO_OLD")

    return as_of, {
        isin_by_warrant[warrant_id]: latest_by_warrant[warrant_id]
        for warrant_id in sorted(latest_by_warrant, key=str)
    }


async def _preview(container: ApplicationContainer) -> dict[str, object]:
    rows = await _bindings(container)
    if not rows:
        raise ValueError("BOUND_GETTEX_POSITIONS_NOT_FOUND")
    for row in rows:
        _validate_binding(row)

    as_of, evidence = await _historical_evidence(
        container,
        tuple(row.warrant_id for row in rows),
    )
    canonical: dict[str, object] = {
        "workspace_id": str(WORKSPACE_ID),
        "provider": MarketDataProvider.GETTEX_DELAYED.value,
        "historical_as_of": as_of.isoformat(),
        "bindings": [_binding_payload(row) for row in rows],
        "historical_evidence": {
            isin: observed.isoformat() for isin, observed in sorted(evidence.items())
        },
    }
    return {
        **canonical,
        "preview_sha256": _digest(canonical),
        "count": len(rows),
    }


async def _apply(
    container: ApplicationContainer,
    *,
    expected_preview_sha256: str,
) -> dict[str, object]:
    preview = await _preview(container)
    if preview["preview_sha256"] != expected_preview_sha256:
        raise ValueError("BOUND_GETTEX_REFRESH_PREVIEW_CHANGED")

    rows = await _bindings(container)
    resolver = build_warrant_quote_resolver(container)
    as_of = datetime.fromisoformat(str(preview["historical_as_of"]))
    results: list[dict[str, object]] = []

    for row in rows:
        resolution = await resolver.resolve_selected(
            MarketDataProvider.GETTEX_DELAYED.value,
            WarrantQuoteRequest(
                workspace_id=WORKSPACE_ID,
                warrant_listing_id=row.warrant_listing_id,
                correlation_id=uuid4(),
                as_of=as_of,
                expected_currency=row.quotation_currency_code,
            ),
        )
        quote = resolution.result.data if resolution.result is not None else None
        results.append(
            {
                "isin": row.isin,
                "position_id": str(row.position_id),
                "listing_id": str(row.warrant_listing_id),
                "selected_source": resolution.selected_source,
                "available": quote is not None,
                "bid": str(quote.bid) if quote is not None and quote.bid is not None else None,
                "ask": str(quote.ask) if quote is not None and quote.ask is not None else None,
                "observed_at": (
                    quote.observed_at.isoformat()
                    if quote is not None and quote.observed_at is not None
                    else None
                ),
                "retrieved_at": (
                    resolution.result.retrieved_at.isoformat()
                    if resolution.result is not None
                    else None
                ),
                "refresh_error": quote.refresh_error if quote is not None else None,
                "attempts": [
                    {
                        "status": attempt.status.value,
                        "reason": attempt.reason,
                    }
                    for attempt in resolution.attempts
                ],
            }
        )

    async with container.database.session_context() as session:
        persisted = set(
            await session.scalars(
                select(WarrantQuoteObservationModel.warrant_listing_id).where(
                    WarrantQuoteObservationModel.workspace_id == WORKSPACE_ID,
                    WarrantQuoteObservationModel.provider
                    == MarketDataProvider.GETTEX_DELAYED.value,
                    WarrantQuoteObservationModel.warrant_listing_id.in_(
                        [row.warrant_listing_id for row in rows]
                    ),
                )
            )
        )

    available = sum(bool(result["available"]) for result in results)
    return {
        "applied": True,
        "preview_sha256": expected_preview_sha256,
        "requested": len(rows),
        "available": available,
        "persisted_observations": len(persisted),
        "failed": len(rows) - available,
        "results": results,
    }


async def run(
    *,
    apply: bool,
    expected_preview_sha256: str | None,
    confirmation: bool,
) -> dict[str, object]:
    settings = get_settings()
    if settings.market_data.refresh.enabled:
        raise ValueError("MARKET_DATA_REFRESH_MUST_BE_DISABLED")
    if settings.market_data.refresh.auto_configure:
        raise ValueError("MARKET_DATA_AUTO_CONFIGURE_MUST_BE_DISABLED")
    if not settings.market_data.gettex_delayed.enabled:
        raise ValueError("GETTEX_DELAYED_MUST_BE_ENABLED")
    if not settings.market_data.gettex_delayed.private_use_confirmed:
        raise ValueError("GETTEX_PRIVATE_USE_CONFIRMATION_REQUIRED")
    if apply and not confirmation:
        raise ValueError("BOUND_GETTEX_REFRESH_CONFIRMATION_REQUIRED")
    if apply and (expected_preview_sha256 is None or len(expected_preview_sha256) != 64):
        raise ValueError("BOUND_GETTEX_REFRESH_PREVIEW_SHA256_REQUIRED")

    container = ApplicationContainer.build(settings)
    try:
        if apply:
            assert expected_preview_sha256 is not None
            return await _apply(
                container,
                expected_preview_sha256=expected_preview_sha256,
            )
        return {"applied": False, **await _preview(container)}
    finally:
        await container.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-preview-sha256")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        run(
            apply=args.apply,
            expected_preview_sha256=args.expected_preview_sha256,
            confirmation=args.confirm,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("applied") and result.get("failed"):
        sys.exit(2)


if __name__ == "__main__":
    main()
