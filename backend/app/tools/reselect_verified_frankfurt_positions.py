"""Preview or atomically reselect verified Frankfurt public quote routes."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.core.di import ApplicationContainer
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import (
    POSITION_QUOTE_SOURCE_POLICY_V1,
)
from app.features.market_data.service.types import MarketDataResult
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
_PROVIDER = MarketDataProvider.FRANKFURT_QUOTES
_RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _require_runtime(container: ApplicationContainer) -> None:
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


def _observation_payload(row: WarrantQuoteObservationModel, *, isin: str) -> dict[str, object]:
    try:
        result = _RESULT.validate_python(row.payload)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ValueError(f"FRANKFURT_OBSERVATION_INVALID_{isin}") from exc

    quote = result.data
    if (
        result.provider is not _PROVIDER
        or quote is None
        or quote.reference_price is None
        or quote.reference_price_type not in {"LAST_TRADE", "PREVIOUS_CLOSE"}
        or quote.bid is not None
        or quote.ask is not None
        or quote.provider_exchange_code != "XSC"
        or quote.venue_mic != "XFRA"
        or quote.currency != "EUR"
        or quote.isin != isin
        or quote.refresh_error is not None
    ):
        raise ValueError(f"FRANKFURT_OBSERVATION_NOT_REFERENCE_USABLE_{isin}")

    return {
        "retrieved_at": result.retrieved_at.isoformat(),
        "observed_at": quote.observed_at.isoformat() if quote.observed_at is not None else None,
        "reference_price": str(quote.reference_price),
        "reference_price_type": quote.reference_price_type,
        "source_mode": quote.source_mode,
    }


async def _candidate_for(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    isin: str,
) -> Any | None:
    repository = PositionQuoteSourceSelectionRepository(session)
    candidates = await repository.verified_candidates(workspace_id, warrant_id)
    if len(candidates) != 1:
        return None
    candidate = candidates[0]
    if (
        candidate.provider is not _PROVIDER
        or candidate.mic != "XFRA"
        or candidate.provider_exchange_code != "XSC"
        or candidate.currency != "EUR"
    ):
        return None
    if candidate.mapping_id is None or not candidate.identity_key:
        raise ValueError(f"FRANKFURT_ROUTE_IDENTITY_INVALID_{isin}")
    return candidate


async def _plan(session: AsyncSession, *, lock: bool) -> dict[str, object]:
    statement = (
        select(
            PositionModel,
            TradeModel,
            WarrantModel,
            PositionQuoteSourceSelectionModel,
        )
        .join(TradeModel, TradeModel.id == PositionModel.trade_id)
        .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
        .join(
            PositionQuoteSourceSelectionModel,
            and_(
                PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                PositionQuoteSourceSelectionModel.workspace_id == TradeModel.workspace_id,
                PositionQuoteSourceSelectionModel.superseded_at.is_(None),
            ),
        )
        .where(
            TradeModel.workspace_id == WORKSPACE_ID,
            TradeModel.cancelled_at.is_(None),
            PositionModel.open_quantity > 0,
            PositionModel.closed_at.is_(None),
            PositionQuoteSourceSelectionModel.selection_status
            == "NO_VERIFIED_QUOTE_SOURCE",
        )
        .order_by(WarrantModel.isin, PositionModel.id)
    )
    if lock:
        statement = statement.with_for_update(of=(PositionModel, PositionQuoteSourceSelectionModel))

    rows = (await session.execute(statement)).all()
    eligible: list[dict[str, object]] = []
    no_verified_mapping = 0
    multiple_or_other_routes = 0

    repository = PositionQuoteSourceSelectionRepository(session)
    for position, trade, warrant, selection in rows:
        candidates = await repository.verified_candidates(trade.workspace_id, warrant.id)
        if not candidates:
            no_verified_mapping += 1
            continue
        if len(candidates) != 1:
            multiple_or_other_routes += 1
            continue

        candidate = await _candidate_for(
            session,
            workspace_id=trade.workspace_id,
            warrant_id=warrant.id,
            isin=warrant.isin,
        )
        if candidate is None:
            multiple_or_other_routes += 1
            continue

        mapping_statement = select(WarrantProviderMappingModel).where(
            WarrantProviderMappingModel.id == candidate.mapping_id,
            WarrantProviderMappingModel.workspace_id == trade.workspace_id,
            WarrantProviderMappingModel.warrant_listing_id == candidate.listing_id,
            WarrantProviderMappingModel.provider == _PROVIDER,
        )
        if lock:
            mapping_statement = mapping_statement.with_for_update()
        mapping = (await session.scalars(mapping_statement)).one_or_none()
        if (
            mapping is None
            or mapping.status is not MappingStatus.ACTIVE
            or mapping.validated_at is None
            or mapping.version != candidate.mapping_version
            or mapping.provider_exchange_code != "XSC"
        ):
            raise ValueError(f"FRANKFURT_MAPPING_CHANGED_{warrant.isin}")

        listing_row = (
            await session.execute(
                select(WarrantListingModel, TradingVenueModel)
                .join(
                    TradingVenueModel,
                    TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                )
                .where(
                    WarrantListingModel.id == candidate.listing_id,
                    WarrantListingModel.workspace_id == trade.workspace_id,
                )
            )
        ).one_or_none()
        if (
            listing_row is None
            or listing_row[1].mic != "XFRA"
            or listing_row[0].quotation_currency_code != "EUR"
        ):
            raise ValueError(f"FRANKFURT_LISTING_CHANGED_{warrant.isin}")

        observation_statement = select(WarrantQuoteObservationModel).where(
            WarrantQuoteObservationModel.workspace_id == trade.workspace_id,
            WarrantQuoteObservationModel.warrant_listing_id == candidate.listing_id,
            WarrantQuoteObservationModel.provider == _PROVIDER.value,
        )
        if lock:
            observation_statement = observation_statement.with_for_update()
        observation = (await session.scalars(observation_statement)).one_or_none()
        if observation is None:
            raise ValueError(f"FRANKFURT_OBSERVATION_MISSING_{warrant.isin}")
        if observation.identity_key != candidate.identity_key:
            raise ValueError(f"FRANKFURT_OBSERVATION_IDENTITY_CHANGED_{warrant.isin}")
        evidence = _observation_payload(observation, isin=warrant.isin)

        eligible.append(
            {
                "position_id": str(position.id),
                "warrant_id": str(warrant.id),
                "isin": warrant.isin,
                "previous_selection_id": str(selection.id),
                "previous_reason": selection.selection_reason,
                "listing_id": str(candidate.listing_id),
                "mapping_id": str(candidate.mapping_id),
                "mapping_version": candidate.mapping_version,
                "identity_key": candidate.identity_key,
                "currency": candidate.currency,
                "listing_mic": candidate.mic,
                "provider_exchange_code": candidate.provider_exchange_code,
                "observation": evidence,
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
            "multiple_or_other_routes": multiple_or_other_routes,
        },
    }
    return {
        **canonical,
        "preview_sha256": _digest(canonical),
        "eligible_count": len(eligible),
        "open_unselected_count": len(rows),
    }


async def _preview(container: ApplicationContainer) -> dict[str, object]:
    _require_runtime(container)
    async with container.database.session_context() as session:
        return await _plan(session, lock=False)


async def _apply(
    container: ApplicationContainer,
    *,
    expected_preview_sha256: str,
) -> dict[str, object]:
    _require_runtime(container)
    async with container.database.session_context() as session:
        plan = await _plan(session, lock=True)
        if plan["preview_sha256"] != expected_preview_sha256:
            raise ValueError("FRANKFURT_RESELECTION_PREVIEW_CHANGED")

        eligible = plan["eligible"]
        if not isinstance(eligible, list) or not eligible:
            raise ValueError("FRANKFURT_RESELECTION_NOTHING_ELIGIBLE")

        when = datetime.now(UTC)
        selected_ids: list[str] = []
        for item in eligible:
            if not isinstance(item, dict):
                raise ValueError("FRANKFURT_RESELECTION_PLAN_INVALID")

            previous_id = UUID(str(item["previous_selection_id"]))
            previous = await session.get(PositionQuoteSourceSelectionModel, previous_id)
            if (
                previous is None
                or previous.superseded_at is not None
                or previous.selection_status != "NO_VERIFIED_QUOTE_SOURCE"
            ):
                raise ValueError("FRANKFURT_RESELECTION_PREVIOUS_DECISION_CHANGED")

            previous.superseded_at = when
            observation = item["observation"]
            assert isinstance(observation, dict)
            new_id = uuid4()
            session.add(
                PositionQuoteSourceSelectionModel(
                    id=new_id,
                    workspace_id=WORKSPACE_ID,
                    position_id=UUID(str(item["position_id"])),
                    warrant_listing_id=UUID(str(item["listing_id"])),
                    warrant_provider_mapping_id=UUID(str(item["mapping_id"])),
                    provider=_PROVIDER.value,
                    identity_key=str(item["identity_key"]),
                    mapping_version=int(item["mapping_version"]),
                    selection_status="SELECTED",
                    selection_reason="RESELECTED_AFTER_VERIFIED_FRANKFURT_OBSERVATION",
                    policy_version=POSITION_QUOTE_SOURCE_POLICY_V1,
                    evidence={
                        "warrant_id": item["warrant_id"],
                        "previous_selection_id": item["previous_selection_id"],
                        "previous_reason": item["previous_reason"],
                        "provider": _PROVIDER.value,
                        "listing_id": item["listing_id"],
                        "mapping_id": item["mapping_id"],
                        "mapping_version": item["mapping_version"],
                        "identity_key": item["identity_key"],
                        "currency": item["currency"],
                        "mic": item["listing_mic"],
                        "provider_exchange_code": item["provider_exchange_code"],
                        "verified_observation": observation,
                        "reselection_preview_sha256": expected_preview_sha256,
                    },
                    selected_at=when,
                    superseded_at=None,
                )
            )
            selected_ids.append(str(new_id))

        await session.flush()
        await session.commit()

    return {
        "applied": True,
        "preview_sha256": expected_preview_sha256,
        "reselected": len(selected_ids),
        "selection_ids": selected_ids,
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
        raise ValueError("FRANKFURT_RESELECTION_CONFIRMATION_REQUIRED")
    if apply and (expected_preview_sha256 is None or len(expected_preview_sha256) != 64):
        raise ValueError("FRANKFURT_RESELECTION_PREVIEW_SHA256_REQUIRED")

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


if __name__ == "__main__":
    main()
