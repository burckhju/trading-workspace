"""Preview or probe unique Frankfurt public-website quote routes for open positions."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.position_monitoring.service.quote_runtime import (
    build_warrant_quote_resolver,
)
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
_PROVIDER = MarketDataProvider.FRANKFURT_QUOTES


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


async def _open_unselected_rows(container: ApplicationContainer) -> list[Any]:
    async with container.database.session_context() as session:
        rows = (
            await session.execute(
                select(
                    PositionModel.id.label("position_id"),
                    PositionModel.product_id.label("warrant_id"),
                    TradeModel.workspace_id,
                    WarrantModel.isin,
                    PositionQuoteSourceSelectionModel.selection_status,
                    PositionQuoteSourceSelectionModel.selection_reason,
                )
                .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
                .join(
                    PositionQuoteSourceSelectionModel,
                    PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                )
                .where(
                    TradeModel.workspace_id == WORKSPACE_ID,
                    TradeModel.cancelled_at.is_(None),
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                    PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                    PositionQuoteSourceSelectionModel.selection_status
                    == "NO_VERIFIED_QUOTE_SOURCE",
                )
                .order_by(WarrantModel.isin, PositionModel.id)
            )
        ).all()
        return list(rows)


async def _preview(container: ApplicationContainer) -> dict[str, object]:
    rows = await _open_unselected_rows(container)
    eligible: list[dict[str, object]] = []
    no_verified_mapping = 0
    multiple_verified_routes = 0
    other_unique_route = 0

    async with container.database.session_context() as session:
        repository = PositionQuoteSourceSelectionRepository(session)
        for row in rows:
            candidates = await repository.verified_candidates(
                row.workspace_id,
                row.warrant_id,
            )
            if not candidates:
                no_verified_mapping += 1
                continue
            if len(candidates) != 1:
                multiple_verified_routes += 1
                continue

            candidate = candidates[0]
            if candidate.provider is not _PROVIDER:
                other_unique_route += 1
                continue
            if (
                candidate.mic != "XFRA"
                or candidate.provider_exchange_code != "XSC"
                or candidate.currency != "EUR"
                or candidate.mapping_id is None
            ):
                raise ValueError(f"FRANKFURT_UNIQUE_ROUTE_IDENTITY_INVALID_{row.isin}")

            eligible.append(
                {
                    "position_id": str(row.position_id),
                    "warrant_id": str(row.warrant_id),
                    "isin": row.isin,
                    "listing_id": str(candidate.listing_id),
                    "mapping_id": str(candidate.mapping_id),
                    "mapping_version": candidate.mapping_version,
                    "identity_key": candidate.identity_key,
                    "currency": candidate.currency,
                    "listing_mic": candidate.mic,
                    "provider_exchange_code": candidate.provider_exchange_code,
                    "selection_status": row.selection_status,
                    "selection_reason": row.selection_reason,
                }
            )

    canonical: dict[str, object] = {
        "workspace_id": str(WORKSPACE_ID),
        "provider": _PROVIDER.value,
        "source_mode": FrankfurtSourceMode.PUBLIC_WEBSITE.value,
        "source_name": "deutsche-boerse-public",
        "eligible": eligible,
        "excluded": {
            "no_verified_mapping": no_verified_mapping,
            "multiple_verified_routes": multiple_verified_routes,
            "other_unique_route": other_unique_route,
        },
    }
    return {
        **canonical,
        "preview_sha256": _digest(canonical),
        "eligible_count": len(eligible),
        "open_unselected_count": len(rows),
    }


def _require_public_runtime(container: ApplicationContainer) -> None:
    settings = container.settings.market_data.frankfurt
    if not settings.enabled:
        raise ValueError("FRANKFURT_MUST_BE_ENABLED")
    if not settings.usage_approved:
        raise ValueError("FRANKFURT_USAGE_APPROVAL_REQUIRED")
    if not settings.contract_verified:
        raise ValueError("FRANKFURT_CONTRACT_VERIFICATION_REQUIRED")
    if settings.source_mode is not FrankfurtSourceMode.PUBLIC_WEBSITE:
        raise ValueError("FRANKFURT_PUBLIC_WEBSITE_MODE_REQUIRED")
    if settings.source_name != "deutsche-boerse-public":
        raise ValueError("FRANKFURT_PUBLIC_SOURCE_NAME_REQUIRED")
    if settings.readiness_reason != "CONFIGURED_NOT_PROBED":
        raise ValueError(settings.readiness_reason)


async def _apply(
    container: ApplicationContainer,
    *,
    expected_preview_sha256: str,
) -> dict[str, object]:
    preview = await _preview(container)
    if preview["preview_sha256"] != expected_preview_sha256:
        raise ValueError("FRANKFURT_PROBE_PREVIEW_CHANGED")

    _require_public_runtime(container)
    resolver = build_warrant_quote_resolver(container)
    results: list[dict[str, object]] = []
    eligible = cast(list[dict[str, object]], preview["eligible"])

    for item in eligible:
        if container.frankfurt is None:
            raise ValueError("FRANKFURT_RUNTIME_NOT_AVAILABLE")
        delay = container.frankfurt.snapshots.request_delay_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        resolution = await resolver.resolve_selected(
            _PROVIDER.value,
            WarrantQuoteRequest(
                workspace_id=WORKSPACE_ID,
                warrant_listing_id=UUID(str(item["listing_id"])),
                correlation_id=uuid4(),
                as_of=datetime.now(UTC),
                expected_currency=str(item["currency"]),
            ),
        )
        quote = resolution.result.data if resolution.result is not None else None
        results.append(
            {
                "isin": item["isin"],
                "position_id": item["position_id"],
                "listing_id": item["listing_id"],
                "selected_source": resolution.selected_source,
                "available": quote is not None,
                "bid": str(quote.bid) if quote is not None and quote.bid is not None else None,
                "ask": str(quote.ask) if quote is not None and quote.ask is not None else None,
                "reference_price": (
                    str(quote.reference_price)
                    if quote is not None and quote.reference_price is not None
                    else None
                ),
                "reference_price_type": (quote.reference_price_type if quote is not None else None),
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

    listing_ids = [UUID(str(item["listing_id"])) for item in eligible]
    async with container.database.session_context() as session:
        persisted = set(
            await session.scalars(
                select(WarrantQuoteObservationModel.warrant_listing_id).where(
                    WarrantQuoteObservationModel.workspace_id == WORKSPACE_ID,
                    WarrantQuoteObservationModel.provider == _PROVIDER.value,
                    WarrantQuoteObservationModel.warrant_listing_id.in_(listing_ids),
                )
            )
        )

    available = sum(bool(result["available"]) for result in results)
    return {
        "applied": True,
        "preview_sha256": expected_preview_sha256,
        "requested": len(results),
        "available": available,
        "persisted_observations": len(persisted),
        "failed": len(results) - available,
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
    if apply and not confirmation:
        raise ValueError("FRANKFURT_PROBE_CONFIRMATION_REQUIRED")
    if apply and (expected_preview_sha256 is None or len(expected_preview_sha256) != 64):
        raise ValueError("FRANKFURT_PROBE_PREVIEW_SHA256_REQUIRED")

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
