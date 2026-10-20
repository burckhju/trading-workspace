"""Read adapter for existing valid-time references and real security listings."""

from dataclasses import replace
from datetime import date
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market.persistence.top_down_models import (
    MarketReferenceListingAssignmentModel,
    MarketReferenceModel,
    ReferenceSeriesDefinitionModel,
    SectorModel,
    SectorReferenceAssignmentModel,
    UnderlyingBenchmarkAssignmentModel,
    UnderlyingSectorAssignmentModel,
)
from app.features.market.service.chart_contracts import (
    ChartIdentity,
    SectorChartContext,
    UnderlyingChartContext,
)
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel


class SqlAlchemyChartContextReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._references: dict[UUID, tuple[ChartIdentity, ...]] = {}
        self._listings: dict[tuple[UUID, UUID], ChartIdentity] = {}

    async def references(self, workspace_id: UUID) -> tuple[ChartIdentity, ...]:
        if workspace_id in self._references:
            return self._references[workspace_id]
        rows = await self._session.execute(
            select(MarketReferenceModel, MarketDataInstrumentModel, ProviderInstrumentMappingModel)
            .outerjoin(
                MarketDataInstrumentModel,
                and_(
                    MarketDataInstrumentModel.market_reference_id == MarketReferenceModel.id,
                    MarketDataInstrumentModel.workspace_id == workspace_id,
                ),
            )
            .outerjoin(
                ProviderInstrumentMappingModel,
                and_(
                    ProviderInstrumentMappingModel.market_data_instrument_id
                    == MarketDataInstrumentModel.id,
                    ProviderInstrumentMappingModel.workspace_id == workspace_id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                ),
            )
            .where(MarketReferenceModel.workspace_id == workspace_id)
            .order_by(MarketReferenceModel.code)
        )
        definitions = tuple(
            (
                await self._session.scalars(
                    select(ReferenceSeriesDefinitionModel)
                    .where(ReferenceSeriesDefinitionModel.workspace_id == workspace_id)
                    .order_by(
                        ReferenceSeriesDefinitionModel.confirmed_at.desc(),
                        ReferenceSeriesDefinitionModel.id,
                    )
                )
            ).all()
        )
        values: list[ChartIdentity] = []
        for reference, instrument, mapping in rows:
            definition = next(
                (
                    item
                    for item in definitions
                    if item.market_reference_id == reference.id
                    and mapping is not None
                    and item.mapping_id == mapping.id
                    and item.mapping_version == mapping.version
                ),
                None,
            )
            values.append(
                ChartIdentity(
                    key=f"reference:{reference.id}",
                    name=reference.name,
                    instrument_id=instrument.id if instrument else None,
                    instrument_type=reference.reference_type,
                    reference_id=reference.id,
                    reference_code=reference.code,
                    return_basis=definition.return_basis if definition else "UNKNOWN",
                    basis_source=definition.source_url if definition else None,
                    active=reference.active,
                    mapping_status=mapping.status.value if mapping else "MISSING",
                    mapping_id=mapping.id if mapping else None,
                    mapping_version=mapping.version if mapping else None,
                    provider_identity=(
                        f"{mapping.provider.value}:{mapping.provider_symbol}.{mapping.provider_exchange_code}"
                        if mapping
                        else None
                    ),
                    setup_url=f"/chart-setup?reference_id={reference.id}",
                )
            )
        result = tuple(values)
        self._references[workspace_id] = result
        return result

    async def resolve(self, workspace_id: UUID, key: str) -> ChartIdentity:
        kind, _, identifier = key.partition(":")
        owner_id = UUID(identifier)
        if kind == "reference":
            result = next(
                (
                    item
                    for item in await self.references(workspace_id)
                    if item.reference_id == owner_id
                ),
                None,
            )
            if result is None:
                raise ValueError("market reference not found in workspace")
            return result
        if kind != "listing":
            raise ValueError("target must address reference or listing")
        cache_key = (workspace_id, owner_id)
        if cache_key in self._listings:
            return self._listings[cache_key]
        row = (
            await self._session.execute(
                select(
                    ListingModel,
                    UnderlyingModel,
                    TradingVenueModel,
                    MarketDataInstrumentModel,
                    ProviderInstrumentMappingModel,
                )
                .join(UnderlyingModel, ListingModel.underlying_id == UnderlyingModel.id)
                .join(TradingVenueModel, ListingModel.trading_venue_id == TradingVenueModel.id)
                .outerjoin(
                    MarketDataInstrumentModel,
                    and_(
                        MarketDataInstrumentModel.listing_id == ListingModel.id,
                        MarketDataInstrumentModel.workspace_id == workspace_id,
                    ),
                )
                .outerjoin(
                    ProviderInstrumentMappingModel,
                    and_(
                        ProviderInstrumentMappingModel.listing_id == ListingModel.id,
                        ProviderInstrumentMappingModel.workspace_id == workspace_id,
                        ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                    ),
                )
                .where(
                    ListingModel.id == owner_id,
                    ListingModel.workspace_id == workspace_id,
                    UnderlyingModel.workspace_id == workspace_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise ValueError("listing not found in workspace")
        listing, underlying, venue, instrument, mapping = row
        result = ChartIdentity(
            key=key,
            name=underlying.name,
            instrument_id=instrument.id if instrument else None,
            instrument_type=underlying.type.value,
            underlying_id=underlying.id,
            listing_id=listing.id,
            isin=underlying.isin,
            ticker=listing.ticker,
            mic=venue.mic,
            currency=listing.currency_code,
            return_basis="SECURITY",
            active=(
                listing.lifecycle_status == LifecycleStatus.ACTIVE
                and underlying.lifecycle_status == LifecycleStatus.ACTIVE
                and venue.is_active
            ),
            mapping_status=mapping.status.value if mapping else "MISSING",
            mapping_id=mapping.id if mapping else None,
            mapping_version=mapping.version if mapping else None,
            provider_identity=(
                f"{mapping.provider.value}:{mapping.provider_symbol}.{mapping.provider_exchange_code}"
                if mapping
                else None
            ),
            setup_url=f"/chart-setup?listing_id={listing.id}",
        )
        self._listings[cache_key] = result
        return result

    async def reference_proxies(self, workspace_id: UUID, as_of: date) -> tuple[ChartIdentity, ...]:
        rows = (
            await self._session.scalars(
                select(MarketReferenceListingAssignmentModel).where(
                    MarketReferenceListingAssignmentModel.workspace_id == workspace_id,
                    MarketReferenceListingAssignmentModel.valid_from <= as_of,
                    or_(
                        MarketReferenceListingAssignmentModel.valid_to.is_(None),
                        MarketReferenceListingAssignmentModel.valid_to >= as_of,
                    ),
                )
            )
        ).all()
        values = []
        for reference in await self.references(workspace_id):
            matches = [row for row in rows if row.market_reference_id == reference.reference_id]
            if (
                not reference.active
                or len(matches) != 1
                or matches[0].quality_status not in {"GOOD", "LIMITED"}
            ):
                continue
            proxy = await self.resolve(workspace_id, f"listing:{matches[0].listing_id}")
            if proxy.instrument_type == "ETF":
                values.append(
                    replace(
                        proxy,
                        reference_id=reference.reference_id,
                        reference_code=reference.reference_code,
                    )
                )
        return tuple(values)

    async def sectors(self, workspace_id: UUID, as_of: date) -> tuple[SectorChartContext, ...]:
        sectors = (
            await self._session.scalars(
                select(SectorModel)
                .where(SectorModel.workspace_id == workspace_id)
                .order_by(SectorModel.classification_system, SectorModel.code)
            )
        ).all()
        assignments = (
            await self._session.scalars(
                select(SectorReferenceAssignmentModel).where(
                    SectorReferenceAssignmentModel.workspace_id == workspace_id,
                    SectorReferenceAssignmentModel.valid_from <= as_of,
                    or_(
                        SectorReferenceAssignmentModel.valid_to.is_(None),
                        SectorReferenceAssignmentModel.valid_to >= as_of,
                    ),
                )
            )
        ).all()
        proxies = (
            await self._session.scalars(
                select(MarketReferenceListingAssignmentModel).where(
                    MarketReferenceListingAssignmentModel.workspace_id == workspace_id,
                    MarketReferenceListingAssignmentModel.valid_from <= as_of,
                    or_(
                        MarketReferenceListingAssignmentModel.valid_to.is_(None),
                        MarketReferenceListingAssignmentModel.valid_to >= as_of,
                    ),
                )
            )
        ).all()
        references = {item.reference_id: item for item in await self.references(workspace_id)}
        result: list[SectorChartContext] = []
        for sector in sectors:
            matches = [item for item in assignments if item.sector_id == sector.id]
            reference = (
                references.get(matches[0].market_reference_id) if len(matches) == 1 else None
            )
            status = "CONFIGURED"
            proxy = None
            if not sector.active:
                status = "INACTIVE_SECTOR"
            elif len(matches) != 1:
                status = "MISSING_REFERENCE" if not matches else "AMBIGUOUS_REFERENCE"
            elif matches[0].quality_status not in {"GOOD", "LIMITED"}:
                status = "INSUFFICIENT_ASSIGNMENT_QUALITY"
                reference = None
            elif reference is None or not reference.active:
                status = "INACTIVE_REFERENCE"
            if reference is not None:
                choices = [
                    item for item in proxies if item.market_reference_id == reference.reference_id
                ]
                if len(choices) > 1:
                    status = "AMBIGUOUS_PROXY"
                elif choices and choices[0].quality_status in {"GOOD", "LIMITED"}:
                    proxy = await self.resolve(workspace_id, f"listing:{choices[0].listing_id}")
                    if proxy.instrument_type != "ETF":
                        status = "PROXY_IS_NOT_ETF"
                elif choices:
                    status = "INSUFFICIENT_PROXY_QUALITY"
            result.append(
                SectorChartContext(
                    sector.id,
                    sector.code,
                    sector.name,
                    sector.classification_system,
                    sector.classification_version,
                    sector.active,
                    reference,
                    proxy,
                    status,
                    f"/chart-setup?sector_id={sector.id}",
                )
            )
        return tuple(result)

    async def underlying(
        self, workspace_id: UUID, underlying_id: UUID, as_of: date
    ) -> UnderlyingChartContext:
        if (
            await self._session.scalar(
                select(UnderlyingModel.id).where(
                    UnderlyingModel.id == underlying_id,
                    UnderlyingModel.workspace_id == workspace_id,
                )
            )
            is None
        ):
            raise ValueError("underlying not found in workspace")
        listings = (
            await self._session.scalars(
                select(ListingModel.id).where(
                    ListingModel.workspace_id == workspace_id,
                    ListingModel.underlying_id == underlying_id,
                    ListingModel.is_primary.is_(True),
                    ListingModel.lifecycle_status == LifecycleStatus.ACTIVE,
                )
            )
        ).all()
        subject = (
            await self.resolve(workspace_id, f"listing:{listings[0]}")
            if len(listings) == 1
            else None
        )
        issues: list[str] = [] if subject else ["NO_UNAMBIGUOUS_PRIMARY_LISTING"]
        benchmarks = (
            await self._session.scalars(
                select(UnderlyingBenchmarkAssignmentModel).where(
                    UnderlyingBenchmarkAssignmentModel.workspace_id == workspace_id,
                    UnderlyingBenchmarkAssignmentModel.underlying_id == underlying_id,
                    UnderlyingBenchmarkAssignmentModel.role == "BROAD_MARKET",
                    UnderlyingBenchmarkAssignmentModel.valid_from <= as_of,
                    or_(
                        UnderlyingBenchmarkAssignmentModel.valid_to.is_(None),
                        UnderlyingBenchmarkAssignmentModel.valid_to >= as_of,
                    ),
                )
            )
        ).all()
        market = None
        if len(benchmarks) == 1 and benchmarks[0].quality_status in {"GOOD", "LIMITED"}:
            market = await self.resolve(
                workspace_id, f"reference:{benchmarks[0].market_reference_id}"
            )
        else:
            issues.append("NO_UNAMBIGUOUS_BENCHMARK")
        memberships = (
            await self._session.scalars(
                select(UnderlyingSectorAssignmentModel).where(
                    UnderlyingSectorAssignmentModel.workspace_id == workspace_id,
                    UnderlyingSectorAssignmentModel.underlying_id == underlying_id,
                    UnderlyingSectorAssignmentModel.valid_from <= as_of,
                    or_(
                        UnderlyingSectorAssignmentModel.valid_to.is_(None),
                        UnderlyingSectorAssignmentModel.valid_to >= as_of,
                    ),
                )
            )
        ).all()
        sector = None
        if len(memberships) == 1 and memberships[0].quality_status in {"GOOD", "LIMITED"}:
            context = next(
                (
                    item
                    for item in await self.sectors(workspace_id, as_of)
                    if item.id == memberships[0].sector_id
                ),
                None,
            )
            if context and context.status == "CONFIGURED":
                # An explicitly assigned proxy is a chosen reference, never a failure fallback.
                sector = context.proxy or context.reference
        if sector is None:
            issues.append("NO_UNAMBIGUOUS_SECTOR_REFERENCE")
        return UnderlyingChartContext(underlying_id, subject, market, sector, tuple(issues), as_of)
