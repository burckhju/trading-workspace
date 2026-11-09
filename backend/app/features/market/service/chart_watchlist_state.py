"""Batch projection of chart membership onto existing owner and historical facts."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus, UnderlyingType
from app.features.market.persistence.chart_watchlist import ChartWatchlistMemberModel
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market.persistence.top_down_models import (
    MarketReferenceModel,
    ReferenceSeriesDefinitionModel,
)
from app.features.market.service.chart_watchlist_catalog import ChartWatchlistDefinition
from app.features.market.service.chart_watchlist_contracts import (
    ChartWatchlistHistory,
    ChartWatchlistItemResponse,
    ChartWatchlistMapping,
)
from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    PriceType,
)
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)


def preview_item(definition: ChartWatchlistDefinition) -> ChartWatchlistItemResponse:
    return ChartWatchlistItemResponse.model_validate(definition.model_dump())


class ChartWatchlistStateReader:
    """Read one bounded member set without provider calls or status writes."""

    def __init__(self, session: AsyncSession, workspace_id: UUID) -> None:
        self._session = session
        self._workspace_id = workspace_id

    async def read(
        self, members: Sequence[ChartWatchlistMemberModel]
    ) -> tuple[ChartWatchlistItemResponse, ...]:
        if not members:
            return ()
        listing_ids = [row.listing_id for row in members if row.listing_id]
        reference_ids = [row.market_reference_id for row in members if row.market_reference_id]
        listings = {
            row.id: row
            for row in await self._session.scalars(
                select(ListingModel).where(
                    ListingModel.workspace_id == self._workspace_id,
                    ListingModel.id.in_(listing_ids),
                )
            )
        }
        underlyings = {
            row.id: row
            for row in await self._session.scalars(
                select(UnderlyingModel).where(
                    UnderlyingModel.workspace_id == self._workspace_id,
                    UnderlyingModel.id.in_([row.underlying_id for row in listings.values()]),
                )
            )
        }
        venues = {
            row.id: row
            for row in await self._session.scalars(
                select(TradingVenueModel).where(
                    TradingVenueModel.id.in_([row.trading_venue_id for row in listings.values()])
                )
            )
        }
        currencies = {
            row.code: row
            for row in await self._session.scalars(
                select(CurrencyModel).where(
                    CurrencyModel.code.in_([row.currency_code for row in listings.values()])
                )
            )
        }
        references = {
            row.id: row
            for row in await self._session.scalars(
                select(MarketReferenceModel).where(
                    MarketReferenceModel.workspace_id == self._workspace_id,
                    MarketReferenceModel.id.in_(reference_ids),
                )
            )
        }
        instruments = tuple(
            await self._session.scalars(
                select(MarketDataInstrumentModel).where(
                    MarketDataInstrumentModel.workspace_id == self._workspace_id,
                    (
                        MarketDataInstrumentModel.listing_id.in_(listing_ids)
                        | MarketDataInstrumentModel.market_reference_id.in_(reference_ids)
                    ),
                )
            )
        )
        instruments_by_owner = {
            (row.listing_id, row.market_reference_id): row for row in instruments
        }
        instrument_ids = [row.id for row in instruments]
        mappings = {
            row.market_data_instrument_id: row
            for row in await self._session.scalars(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == self._workspace_id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                    ProviderInstrumentMappingModel.market_data_instrument_id.in_(instrument_ids),
                )
            )
        }
        basis_definitions = (
            tuple(
                await self._session.scalars(
                    select(ReferenceSeriesDefinitionModel).where(
                        ReferenceSeriesDefinitionModel.workspace_id == self._workspace_id,
                        ReferenceSeriesDefinitionModel.market_reference_id.in_(reference_ids),
                    )
                )
            )
            if reference_ids
            else ()
        )
        histories = {
            row[0]: ChartWatchlistHistory(
                observation_count=row[1],
                first_date=row[2],
                last_date=row[3],
                last_received_at=row[4],
            )
            for row in await self._session.execute(
                select(
                    DailyPriceModel.market_data_instrument_id,
                    func.count(DailyPriceModel.id),
                    func.min(DailyPriceModel.trading_date),
                    func.max(DailyPriceModel.trading_date),
                    func.max(DailyPriceModel.retrieved_at),
                )
                .where(
                    DailyPriceModel.workspace_id == self._workspace_id,
                    DailyPriceModel.market_data_instrument_id.in_(instrument_ids),
                    DailyPriceModel.price_type == PriceType.EOD,
                )
                .group_by(DailyPriceModel.market_data_instrument_id)
            )
        }
        result = []
        for member in members:
            definition = ChartWatchlistDefinition.model_validate(member.definition)
            item = preview_item(definition)
            item.last_attempt_at = member.last_attempt_at
            item.setup_completed_at = member.setup_completed_at
            instrument = instruments_by_owner.get((member.listing_id, member.market_reference_id))
            mapping = mappings.get(instrument.id) if instrument else None
            if instrument is not None:
                item.history = histories.get(instrument.id, ChartWatchlistHistory())
            if mapping is not None:
                item.mapping = ChartWatchlistMapping(
                    id=mapping.id,
                    version=mapping.version,
                    status=mapping.status.value,
                    provider_symbol=mapping.provider_symbol,
                    provider_exchange_code=mapping.provider_exchange_code,
                    validated_at=mapping.validated_at,
                )
            if definition.kind == "INDEX":
                reference = (
                    references.get(member.market_reference_id)
                    if member.market_reference_id
                    else None
                )
                reason = reference_reason(definition, reference)
                if mapping is not None and (
                    mapping.provider_symbol != "GSPC" or mapping.provider_exchange_code != "INDX"
                ):
                    reason = "EXISTING_PROVIDER_MAPPING_CONFLICT"
                if (
                    mapping is not None
                    and mapping.status == MappingStatus.ACTIVE
                    and definition.return_basis is not None
                    and not reason
                    and (
                        member.setup_completed_at is None
                        or member.verified_mapping_version == mapping.version
                    )
                ):
                    definitions = [
                        row
                        for row in basis_definitions
                        if row.market_reference_id == member.market_reference_id
                        and row.mapping_id == mapping.id
                        and row.mapping_version == mapping.version
                    ]
                    if any(row.return_basis != definition.return_basis for row in definitions):
                        reason = "EXISTING_INDEX_RETURN_BASIS_CONFLICT"
                    elif not definitions:
                        reason = "INDEX_RETURN_BASIS_REQUIRED"
                if reference is not None:
                    item.target_key = f"reference:{reference.id}"
            else:
                listing = listings.get(member.listing_id) if member.listing_id else None
                reason = listing_reason(
                    definition,
                    listing,
                    underlyings.get(listing.underlying_id) if listing else None,
                    venues.get(listing.trading_venue_id) if listing else None,
                    currencies.get(listing.currency_code) if listing else None,
                )
                if listing is not None:
                    item.target_key = f"listing:{listing.id}"
            if member.listing_id is None and member.market_reference_id is None:
                item.setup_reason = member.last_attempt_reason
                item.setup_status = "BLOCKED" if item.setup_reason else "PENDING"
            elif reason:
                item.setup_status, item.setup_reason = "BLOCKED", reason
            elif mapping is None:
                item.setup_status = "BLOCKED" if member.last_attempt_reason else "PENDING"
                item.setup_reason = member.last_attempt_reason or "EODHD_MAPPING_REQUIRED"
            elif mapping.status != MappingStatus.ACTIVE or mapping.validated_at is None:
                item.setup_status = "BLOCKED"
                item.setup_reason = member.last_attempt_reason or "VALIDATED_EODHD_MAPPING_REQUIRED"
            elif mapping.listing_id != member.listing_id:
                item.setup_status, item.setup_reason = (
                    "BLOCKED",
                    "MAPPING_OWNER_CONFLICT",
                )
            elif member.setup_completed_at is None and member.last_attempt_reason:
                item.setup_status, item.setup_reason = (
                    "BLOCKED",
                    member.last_attempt_reason,
                )
            elif member.setup_completed_at is None:
                item.setup_status, item.setup_reason = (
                    "PENDING",
                    "MAPPING_CONFIRMATION_PENDING",
                )
            elif (
                member.verified_mapping_id != mapping.id
                or member.verified_mapping_version != mapping.version
                or member.verified_provider_symbol != mapping.provider_symbol
                or member.verified_provider_exchange_code != mapping.provider_exchange_code
            ):
                item.setup_status = "BLOCKED"
                item.setup_reason = "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP"
            else:
                item.setup_status = "CONFIGURED"
                item.setup_reason = None
            result.append(item)
        return tuple(result)


def reference_reason(
    definition: ChartWatchlistDefinition, reference: MarketReferenceModel | None
) -> str | None:
    if reference is None:
        return "MARKET_REFERENCE_REQUIRED"
    if not reference.active:
        return "MARKET_REFERENCE_INACTIVE"
    if reference.code != definition.code or reference.reference_type != "INDEX":
        return "MARKET_REFERENCE_IDENTITY_CONFLICT"
    return None


def listing_reason(
    definition: ChartWatchlistDefinition,
    listing: ListingModel | None,
    underlying: UnderlyingModel | None,
    venue: TradingVenueModel | None,
    currency: CurrencyModel | None,
) -> str | None:
    if listing is None or underlying is None:
        return "ETF_LISTING_REQUIRED"
    if (
        listing.lifecycle_status != LifecycleStatus.ACTIVE
        or underlying.lifecycle_status != LifecycleStatus.ACTIVE
    ):
        return "ETF_MASTER_DATA_INACTIVE"
    if venue is None or not venue.is_active:
        return "TRADING_VENUE_INACTIVE_OR_MISSING"
    if currency is None or not currency.is_active:
        return "CURRENCY_INACTIVE_OR_MISSING"
    if (
        underlying.type != UnderlyingType.ETF
        or underlying.isin != definition.isin
        or venue.mic != definition.mic
        or listing.currency_code != definition.currency
        or listing.ticker != definition.ticker
    ):
        return "ETF_LISTING_IDENTITY_CONFLICT"
    return None
