"""Resume one confirmed member through the released master-data and mapping owners."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Protocol, cast
from uuid import UUID, uuid4

from sqlalchemy import select
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
    ChartWatchlistError,
    ChartWatchlistMapping,
)
from app.features.market.service.chart_watchlist_state import (
    listing_reason,
    reference_reason,
)
from app.features.market.service.currency_administration import (
    CurrencyAdministrationService,
)
from app.features.market.service.listing_service import ListingService
from app.features.market.service.service import UnderlyingService
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market.service.trading_venue_administration import (
    TradingVenueAdministrationService,
)
from app.features.market.service.types import (
    Actor,
    AddListing,
    CreateListing,
    CreateTradingVenue,
    CreateUnderlying,
)
from app.features.market.service.unit_of_work import SqlAlchemyMarketUnitOfWork
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.contracts import ProviderInstrumentResolver
from app.features.market_data.service.instrument_identity import (
    MarketDataInstrumentIdentityService,
)
from app.features.market_data.service.reference_market_data import (
    ReferenceMarketDataService,
)
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VerifiedListingVenue,
)
from app.providers.eodhd.etf_catalog import EtfCatalogIdentity
from app.providers.eodhd.reference_catalog import TOP_DOWN_V1_EODHD_SUGGESTIONS


class ChartEtfDiscovery(Protocol):
    async def verify(
        self,
        *,
        isin: str,
        currency: str,
        mic: str,
        listing_ticker: str,
        listing_source_url: str,
        listing_reviewed_on: date,
        venue_source_url: str,
    ) -> EtfCatalogIdentity: ...


EtfResolverFactory = Callable[
    [AsyncSession, UUID, UUID, EtfCatalogIdentity], ProviderInstrumentResolver
]
ReferenceServiceFactory = Callable[[Callable[[], UUID]], ReferenceMarketDataService]


class ChartWatchlistSetup:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        *,
        etf_discovery: ChartEtfDiscovery | None,
        etf_resolver_factory: EtfResolverFactory | None,
        reference_service: ReferenceMarketDataService | None,
        reference_service_factory: ReferenceServiceFactory | None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._discovery = etf_discovery
        self._resolver_factory = etf_resolver_factory
        self._reference_service = reference_service
        self._reference_factory = reference_service_factory

    async def configure(
        self,
        member: ChartWatchlistMemberModel,
        definition: ChartWatchlistDefinition,
        actor: Actor,
    ) -> ChartWatchlistMapping:
        if definition.kind == "INDEX":
            return await self._index(member, definition, actor)
        return await self._etf(member, definition, actor)

    async def _index(
        self,
        member: ChartWatchlistMemberModel,
        definition: ChartWatchlistDefinition,
        actor: Actor,
    ) -> ChartWatchlistMapping:
        reference = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.workspace_id == self._workspace_id,
                MarketReferenceModel.code == definition.code,
            )
        )
        if reference is not None:
            reason = reference_reason(definition, reference)
            if reason:
                raise ChartWatchlistError(reason)
            if member.market_reference_id not in (None, reference.id):
                raise ChartWatchlistError("MARKET_REFERENCE_IDENTITY_CONFLICT")
        if self._reference_service is None:
            raise ChartWatchlistError("EODHD_DISABLED")
        if reference is None:
            reference = await TopDownReferenceAdministrationService(
                self._session
            ).ensure_v1_reference(self._workspace_id, definition.code)
        member.market_reference_id = reference.id
        await self._session.commit()
        suggestion = next(
            row for row in TOP_DOWN_V1_EODHD_SUGGESTIONS if row.reference_code == definition.code
        )
        symbol, exchange = suggestion.provider_symbol, suggestion.provider_exchange_code
        if symbol is None or exchange is None:
            raise ChartWatchlistError("DOCUMENTED_INDEX_PROVIDER_IDENTITY_REQUIRED")
        mapping = await self._session.scalar(
            select(ProviderInstrumentMappingModel)
            .join(
                MarketDataInstrumentModel,
                ProviderInstrumentMappingModel.market_data_instrument_id
                == MarketDataInstrumentModel.id,
            )
            .where(
                ProviderInstrumentMappingModel.workspace_id == self._workspace_id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                MarketDataInstrumentModel.workspace_id == self._workspace_id,
                MarketDataInstrumentModel.market_reference_id == reference.id,
            )
        )
        if mapping is not None:
            self._same_provider_identity(mapping, symbol, exchange)
            if mapping.listing_id is not None:
                raise ChartWatchlistError("MAPPING_OWNER_CONFLICT")
            if self._active(mapping):
                await self._index_basis(definition, reference.id, mapping, actor)
                return self._binding(mapping)
            self._require_owned_attempt(member, mapping)
        else:
            await self._require_unowned_provider_identity(symbol, exchange)
            if self._reference_factory is None:
                raise ChartWatchlistError("INDEX_MAPPING_FACTORY_REQUIRED")
            reserved_id = uuid4()
            member.created_mapping_id = reserved_id
            member.created_mapping_version = 1
            # The deferred FK and owner commit make creation + ownership evidence atomic.
            creator = self._reference_factory(lambda: reserved_id)
            mapping = await creator.upsert_mapping(
                workspace_id=self._workspace_id,
                market_reference_id=reference.id,
                provider_symbol=symbol,
                provider_exchange_code=exchange,
                require_absent=True,
            )
        member.created_mapping_version = mapping.version + 1
        result = await self._reference_service.validate_mapping(
            workspace_id=self._workspace_id, market_reference_id=reference.id
        )
        if not self._active(result):
            raise ChartWatchlistError("INDEX_PROVIDER_IDENTITY_NOT_VALIDATED")
        await self._index_basis(definition, reference.id, result, actor)
        return self._binding(result)

    async def _index_basis(
        self,
        definition: ChartWatchlistDefinition,
        reference_id: UUID,
        mapping: ProviderInstrumentMappingModel,
        actor: Actor,
    ) -> None:
        if definition.return_basis is None:
            return
        assert definition.basis_source_url
        if (
            definition.code != "SP500"
            or mapping.provider_symbol != "GSPC"
            or mapping.provider_exchange_code != "INDX"
            or not self._active(mapping)
        ):
            raise ChartWatchlistError("INDEX_RETURN_BASIS_IDENTITY_CONFLICT")
        definitions = tuple(
            await self._session.scalars(
                select(ReferenceSeriesDefinitionModel).where(
                    ReferenceSeriesDefinitionModel.workspace_id == self._workspace_id,
                    ReferenceSeriesDefinitionModel.market_reference_id == reference_id,
                    ReferenceSeriesDefinitionModel.mapping_id == mapping.id,
                    ReferenceSeriesDefinitionModel.mapping_version == mapping.version,
                )
            )
        )
        if any(row.return_basis != definition.return_basis for row in definitions):
            raise ChartWatchlistError("EXISTING_INDEX_RETURN_BASIS_CONFLICT")
        if definitions:
            return
        await TopDownReferenceAdministrationService(self._session).confirm_series_basis(
            workspace_id=self._workspace_id,
            market_reference_id=reference_id,
            mapping_id=mapping.id,
            mapping_version=mapping.version,
            return_basis=definition.return_basis,
            source_url=definition.basis_source_url,
            actor=actor.display_name,
        )

    async def _etf(
        self,
        member: ChartWatchlistMemberModel,
        definition: ChartWatchlistDefinition,
        actor: Actor,
    ) -> ChartWatchlistMapping:
        assert definition.isin and definition.currency and definition.mic and definition.ticker
        assert definition.venue_source_url
        underlying = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == self._workspace_id,
                UnderlyingModel.isin == definition.isin,
            )
        )
        if underlying is not None:
            if underlying.type != UnderlyingType.ETF:
                raise ChartWatchlistError("UNDERLYING_TYPE_CONFLICT")
            if underlying.lifecycle_status != LifecycleStatus.ACTIVE:
                raise ChartWatchlistError("ETF_MASTER_DATA_INACTIVE")
        currency = await self._session.get(CurrencyModel, definition.currency)
        if currency is not None and not currency.is_active:
            raise ChartWatchlistError("CURRENCY_INACTIVE")
        venue = await self._session.scalar(
            select(TradingVenueModel).where(TradingVenueModel.mic == definition.mic)
        )
        if venue is not None:
            self._check_venue(definition, venue)
        listing = await self._find_listing(member, definition, underlying, venue)
        if listing is not None:
            reason = listing_reason(definition, listing, underlying, venue, currency)
            if reason:
                raise ChartWatchlistError(reason)
        mapping = await self._listing_mapping(listing.id) if listing else None
        if mapping is not None and not self._active(mapping):
            self._require_owned_attempt(member, mapping)
        if self._discovery is None or self._resolver_factory is None:
            raise ChartWatchlistError("EODHD_DISABLED")
        source = next(
            (
                value["url"]
                for value in definition.sources
                if value.get("role") == "listing_and_etf_type"
            ),
            definition.source_url,
        )
        proof = await self._discovery.verify(
            isin=definition.isin,
            currency=definition.currency,
            mic=definition.mic,
            listing_ticker=definition.ticker,
            listing_source_url=source,
            listing_reviewed_on=definition.reviewed_on,
            venue_source_url=definition.venue_source_url,
        )
        if (
            proof.item.isin != definition.isin
            or proof.item.currency != definition.currency
            or proof.mic != definition.mic
            or proof.listing_ticker != definition.ticker
            or proof.item.provider != MarketDataProvider.EODHD
            or (proof.item.instrument_type or "").upper() != "ETF"
        ):
            raise ChartWatchlistError("ETF_PROVIDER_IDENTITY_CONFLICT")
        symbol, exchange = proof.item.provider_symbol, proof.item.provider_exchange_code
        if mapping is not None:
            self._same_provider_identity(mapping, symbol, exchange)
        else:
            await self._require_unowned_provider_identity(symbol, exchange)
        if currency is None:
            await self._create_currency(definition.currency, actor)
        if venue is None:
            assert definition.exchange_name and definition.country_code and definition.timezone
            venue = await TradingVenueAdministrationService(
                SqlAlchemyMarketUnitOfWork(self._session)
            ).create(
                CreateTradingVenue(
                    actor,
                    definition.mic,
                    definition.exchange_name,
                    definition.country_code,
                    definition.timezone,
                )
            )
        if underlying is None:
            underlying = await UnderlyingService(SqlAlchemyMarketUnitOfWork(self._session)).create(
                CreateUnderlying(
                    self._workspace_id,
                    actor,
                    definition.name,
                    CreateListing(venue.id, definition.ticker, definition.currency),
                    type=UnderlyingType.ETF,
                    isin=definition.isin,
                )
            )
            listing = await self._find_listing(member, definition, underlying, venue)
        elif listing is None:
            listing = await ListingService(SqlAlchemyMarketUnitOfWork(self._session)).add(
                AddListing(
                    self._workspace_id,
                    underlying.id,
                    actor,
                    venue.id,
                    definition.ticker,
                    definition.currency,
                )
            )
        if listing is None:
            raise ChartWatchlistError("ETF_LISTING_REQUIRED")
        member.listing_id = listing.id
        await self._session.commit()
        if mapping is not None and self._active(mapping):
            await self._require_mapping_instrument(mapping, listing.id)
            return self._binding(mapping)
        uow = SqlAlchemyMarketDataUnitOfWork(self._session)
        reserved_id = uuid4()
        owner = ProviderMappingAdministrationService(
            uow,
            mapping_id_factory=lambda: reserved_id,
            resolver=self._resolver_factory(self._session, self._workspace_id, listing.id, proof),
            venue_reconciliation=ProviderVenueReconciliationService(
                uow,
                verified_listing=VerifiedListingVenue(
                    self._workspace_id,
                    listing.id,
                    MarketDataProvider.EODHD,
                    exchange,
                    venue.id,
                ),
            ),
            instrument_identity=MarketDataInstrumentIdentityService(self._session),
        )
        if mapping is None:
            member.created_mapping_id = reserved_id
            member.created_mapping_version = 1
            created = await owner.create_or_update(
                MappingCommand(
                    self._workspace_id,
                    listing.id,
                    MarketDataProvider.EODHD,
                    symbol,
                    exchange,
                    actor.id,
                    actor.display_name,
                    require_absent=True,
                )
            )
            mapping_id, version = created.id, created.version
        else:
            mapping_id, version = mapping.id, mapping.version
        member.created_mapping_version = version + 1
        validated = await owner.validate(
            self._workspace_id,
            mapping_id,
            actor_id=actor.id,
            actor_name=actor.display_name,
        )
        if validated.status != MappingStatus.ACTIVE or validated.validated_at is None:
            raise ChartWatchlistError("ETF_PROVIDER_IDENTITY_NOT_VALIDATED")
        return self._binding(validated)

    async def _find_listing(
        self,
        member: ChartWatchlistMemberModel,
        definition: ChartWatchlistDefinition,
        underlying: UnderlyingModel | None,
        venue: TradingVenueModel | None,
    ) -> ListingModel | None:
        if member.listing_id is not None:
            listing = await self._session.get(
                ListingModel, member.listing_id, populate_existing=True
            )
        elif venue is not None:
            listing = await self._session.scalar(
                select(ListingModel).where(
                    ListingModel.workspace_id == self._workspace_id,
                    ListingModel.trading_venue_id == venue.id,
                    ListingModel.ticker == definition.ticker,
                )
            )
        else:
            listing = None
        if listing is not None and (
            underlying is None
            or listing.workspace_id != self._workspace_id
            or listing.underlying_id != underlying.id
        ):
            raise ChartWatchlistError("ETF_LISTING_IDENTITY_CONFLICT")
        return listing

    async def _listing_mapping(self, listing_id: UUID) -> ProviderInstrumentMappingModel | None:
        return cast(
            ProviderInstrumentMappingModel | None,
            await self._session.scalar(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == self._workspace_id,
                    ProviderInstrumentMappingModel.listing_id == listing_id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                )
            ),
        )

    async def _require_mapping_instrument(
        self, mapping: ProviderInstrumentMappingModel, listing_id: UUID
    ) -> None:
        instrument = (
            await self._session.get(MarketDataInstrumentModel, mapping.market_data_instrument_id)
            if mapping.market_data_instrument_id is not None
            else None
        )
        if (
            instrument is None
            or instrument.workspace_id != self._workspace_id
            or instrument.listing_id != listing_id
            or instrument.market_reference_id is not None
        ):
            raise ChartWatchlistError("MAPPING_INSTRUMENT_IDENTITY_CONFLICT")

    async def _require_unowned_provider_identity(self, symbol: str, exchange: str) -> None:
        owner = await self._session.scalar(
            select(ProviderInstrumentMappingModel.id).where(
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                ProviderInstrumentMappingModel.provider_symbol == symbol,
                ProviderInstrumentMappingModel.provider_exchange_code == exchange,
            )
        )
        if owner is not None:
            raise ChartWatchlistError("EODHD_PROVIDER_IDENTITY_ALREADY_MAPPED")

    async def _create_currency(self, code: str, actor: Actor) -> None:
        owner = CurrencyAdministrationService(self._session)
        admin = await owner.list_admin()
        entry = next((row for row in admin["items"] if row["code"] == code), None)
        if entry is None or not entry["catalog_available"]:
            raise ChartWatchlistError("CURRENCY_CATALOG_REQUIRED")
        if entry["local_exists"] or not entry["can_activate"]:
            raise ChartWatchlistError("CURRENCY_REFERENCE_CONFLICT")
        await owner.change_status(
            code, active=True, expected_token=entry["state_token"], actor=actor
        )

    @staticmethod
    def _active(mapping: ProviderInstrumentMappingModel) -> bool:
        return mapping.status == MappingStatus.ACTIVE and mapping.validated_at is not None

    @staticmethod
    def _binding(
        mapping: ProviderInstrumentMappingModel | ProviderInstrumentMapping,
    ) -> ChartWatchlistMapping:
        return ChartWatchlistMapping(
            id=mapping.id,
            version=mapping.version,
            status=mapping.status.value,
            provider_symbol=mapping.provider_symbol,
            provider_exchange_code=mapping.provider_exchange_code,
            validated_at=mapping.validated_at,
        )

    @staticmethod
    def _check_venue(definition: ChartWatchlistDefinition, venue: TradingVenueModel) -> None:
        if not venue.is_active:
            raise ChartWatchlistError("TRADING_VENUE_INACTIVE")
        if venue.country_code != definition.country_code or venue.timezone != definition.timezone:
            raise ChartWatchlistError("TRADING_VENUE_REFERENCE_CONFLICT")

    @staticmethod
    def _same_provider_identity(
        mapping: ProviderInstrumentMappingModel, symbol: str, exchange: str
    ) -> None:
        if mapping.provider_symbol != symbol or mapping.provider_exchange_code != exchange:
            raise ChartWatchlistError("EXISTING_PROVIDER_MAPPING_CONFLICT")

    @staticmethod
    def _require_owned_attempt(
        member: ChartWatchlistMemberModel, mapping: ProviderInstrumentMappingModel
    ) -> None:
        if (
            member.created_mapping_id != mapping.id
            or member.created_mapping_version != mapping.version
        ):
            raise ChartWatchlistError("EXISTING_INACTIVE_MAPPING_PRESERVED")
