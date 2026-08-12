"""Administrative service for provider-neutral top-down reference configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.persistence.models import (
    MarketAnalysisModel,
    MarketAnalysisRunModel,
)
from app.features.market.domain.top_down import BenchmarkRole, MarketReferenceType
from app.features.market.persistence.models import ListingModel, UnderlyingModel
from app.features.market.persistence.top_down_models import (
    MarketReferenceListingAssignmentModel,
    MarketReferenceModel,
    SectorModel,
    SectorReferenceAssignmentModel,
    UnderlyingBenchmarkAssignmentModel,
    UnderlyingSectorAssignmentModel,
)
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)


@dataclass(frozen=True, slots=True)
class TopDownReferenceReadiness:
    reference_id: UUID
    reference_code: str
    reference_type: str
    listing_id: UUID | None
    provider_mapping_id: UUID | None
    provider_mapping_active: bool
    daily_price_count: int
    latest_price_date: date | None
    completed_analysis_id: UUID | None
    completed_analysis_version: int | None
    ready: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopDownV1BootstrapResult:
    market_references: tuple[MarketReferenceModel, ...]


class TopDownReferenceAdministrationService:
    """Create and connect semantic top-down references without provider coupling."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_market_references(
        self, workspace_id: UUID
    ) -> tuple[MarketReferenceModel, ...]:
        rows = await self._session.scalars(
            select(MarketReferenceModel)
            .where(MarketReferenceModel.workspace_id == workspace_id)
            .order_by(MarketReferenceModel.region, MarketReferenceModel.code)
        )
        return tuple(rows.all())

    async def reference_readiness(
        self, workspace_id: UUID
    ) -> tuple[TopDownReferenceReadiness, ...]:
        """Report whether semantic references can participate in a real top-down run."""
        references = await self.list_market_references(workspace_id)
        results: list[TopDownReferenceReadiness] = []
        today = datetime.now(UTC).date()
        for reference in references:
            blockers: list[str] = []
            assignment = await self._session.scalar(
                select(MarketReferenceListingAssignmentModel)
                .where(
                    MarketReferenceListingAssignmentModel.workspace_id == workspace_id,
                    MarketReferenceListingAssignmentModel.market_reference_id
                    == reference.id,
                    MarketReferenceListingAssignmentModel.valid_from <= today,
                    or_(
                        MarketReferenceListingAssignmentModel.valid_to.is_(None),
                        MarketReferenceListingAssignmentModel.valid_to >= today,
                    ),
                )
                .order_by(MarketReferenceListingAssignmentModel.valid_from.desc())
            )
            listing_id = assignment.listing_id if assignment is not None else None
            if assignment is None:
                blockers.append("NO_ACTIVE_LISTING_ASSIGNMENT")

            mapping = None
            if listing_id is not None:
                mapping = await self._session.scalar(
                    select(ProviderInstrumentMappingModel).where(
                        ProviderInstrumentMappingModel.workspace_id == workspace_id,
                        ProviderInstrumentMappingModel.listing_id == listing_id,
                        ProviderInstrumentMappingModel.provider
                        == MarketDataProvider.EODHD,
                    )
                )
            mapping_active = (
                mapping is not None and mapping.status is MappingStatus.ACTIVE
            )
            if mapping is None:
                blockers.append("NO_EODHD_PROVIDER_MAPPING")
            elif not mapping_active:
                blockers.append("EODHD_PROVIDER_MAPPING_NOT_ACTIVE")

            price_count = 0
            latest_price_date = None
            if listing_id is not None:
                price_count, latest_price_date = (
                    await self._session.execute(
                        select(
                            func.count(DailyPriceModel.id),
                            func.max(DailyPriceModel.trading_date),
                        ).where(
                            DailyPriceModel.workspace_id == workspace_id,
                            DailyPriceModel.listing_id == listing_id,
                        )
                    )
                ).one()
                price_count = int(price_count or 0)
            if price_count < 61:
                blockers.append("INSUFFICIENT_DAILY_PRICE_HISTORY")

            analysis_id = None
            analysis_version = None
            if listing_id is not None:
                row = (
                    await self._session.execute(
                        select(MarketAnalysisModel.id, MarketAnalysisRunModel.version)
                        .join(
                            MarketAnalysisRunModel,
                            MarketAnalysisRunModel.analysis_id
                            == MarketAnalysisModel.id,
                        )
                        .where(
                            MarketAnalysisModel.workspace_id == workspace_id,
                            MarketAnalysisModel.listing_id == listing_id,
                            MarketAnalysisRunModel.status
                            == AnalysisStatus.COMPLETED.value,
                        )
                        .order_by(
                            MarketAnalysisRunModel.analysis_time.desc(),
                            MarketAnalysisRunModel.version.desc(),
                        )
                        .limit(1)
                    )
                ).first()
                if row is not None:
                    analysis_id, analysis_version = row
            if analysis_id is None:
                blockers.append("NO_COMPLETED_MARKET_ANALYSIS")

            results.append(
                TopDownReferenceReadiness(
                    reference_id=reference.id,
                    reference_code=reference.code,
                    reference_type=reference.reference_type,
                    listing_id=listing_id,
                    provider_mapping_id=mapping.id if mapping is not None else None,
                    provider_mapping_active=mapping_active,
                    daily_price_count=price_count,
                    latest_price_date=latest_price_date,
                    completed_analysis_id=analysis_id,
                    completed_analysis_version=analysis_version,
                    ready=not blockers,
                    blockers=tuple(blockers),
                )
            )
        return tuple(results)

    async def list_sectors(self, workspace_id: UUID) -> tuple[SectorModel, ...]:
        rows = await self._session.scalars(
            select(SectorModel)
            .where(SectorModel.workspace_id == workspace_id)
            .order_by(SectorModel.code)
        )
        return tuple(rows.all())

    async def bootstrap_v1(self, workspace_id: UUID) -> TopDownV1BootstrapResult:
        """Idempotently create the approved V1 semantic benchmark references.

        Provider symbols and listings are intentionally not guessed here.  They are
        connected explicitly through market-reference listing assignments and the
        existing provider-mapping administration API.
        """
        definitions = (
            ("DAX", "DAX", "DE", BenchmarkRole.BROAD_MARKET),
            ("SP500", "S&P 500", "US", BenchmarkRole.BROAD_MARKET),
            ("NASDAQ100", "Nasdaq-100", "US", BenchmarkRole.GROWTH_TECH),
        )
        now = datetime.now(UTC)
        values: list[MarketReferenceModel] = []
        for code, name, region, role in definitions:
            existing = await self._session.scalar(
                select(MarketReferenceModel).where(
                    MarketReferenceModel.workspace_id == workspace_id,
                    MarketReferenceModel.code == code,
                )
            )
            if existing is None:
                existing = MarketReferenceModel(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    code=code,
                    name=name,
                    reference_type=MarketReferenceType.INDEX.value,
                    region=region,
                    role=role.value,
                    reference_version="TOP_DOWN_V1",
                    active=True,
                    created_at=now,
                )
                self._session.add(existing)
            values.append(existing)
        await self._session.commit()
        return TopDownV1BootstrapResult(tuple(values))

    async def create_sector(
        self,
        *,
        workspace_id: UUID,
        code: str,
        name: str,
        classification_system: str,
        classification_version: str,
    ) -> SectorModel:
        normalized = code.strip().upper()
        existing = await self._session.scalar(
            select(SectorModel).where(
                SectorModel.workspace_id == workspace_id,
                SectorModel.code == normalized,
            )
        )
        if existing is not None:
            raise ValueError("sector code already exists")
        value = SectorModel(
            id=uuid4(),
            workspace_id=workspace_id,
            code=normalized,
            name=name.strip(),
            classification_system=classification_system.strip(),
            classification_version=classification_version.strip(),
            active=True,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def set_market_reference_active(
        self, *, workspace_id: UUID, market_reference_id: UUID, active: bool
    ) -> MarketReferenceModel:
        value = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.id == market_reference_id,
            )
        )
        if value is None:
            raise ValueError("market reference not found")
        value.active = active
        await self._session.commit()
        return value

    async def set_sector_active(
        self, *, workspace_id: UUID, sector_id: UUID, active: bool
    ) -> SectorModel:
        value = await self._session.scalar(
            select(SectorModel).where(
                SectorModel.workspace_id == workspace_id,
                SectorModel.id == sector_id,
            )
        )
        if value is None:
            raise ValueError("sector not found")
        value.active = active
        await self._session.commit()
        return value

    async def assign_reference_listing(
        self,
        *,
        workspace_id: UUID,
        market_reference_id: UUID,
        listing_id: UUID,
        valid_from: date,
        valid_to: date | None,
        source: str,
        source_reference: str | None,
        quality_status: str,
    ) -> MarketReferenceListingAssignmentModel:
        await self._require_reference(workspace_id, market_reference_id)
        listing = await self._session.scalar(
            select(ListingModel).where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.id == listing_id,
            )
        )
        if listing is None:
            raise ValueError("listing not found in workspace")
        await self._ensure_no_overlap(
            MarketReferenceListingAssignmentModel,
            workspace_id,
            valid_from,
            valid_to,
            MarketReferenceListingAssignmentModel.market_reference_id
            == market_reference_id,
            label="market-reference listing assignment",
        )
        value = MarketReferenceListingAssignmentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            market_reference_id=market_reference_id,
            listing_id=listing_id,
            valid_from=valid_from,
            valid_to=valid_to,
            source=source.strip(),
            source_reference=self._clean(source_reference),
            quality_status=quality_status,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def assign_underlying_benchmark(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        market_reference_id: UUID,
        role: BenchmarkRole,
        valid_from: date,
        valid_to: date | None,
        source: str,
        source_reference: str | None,
        quality_status: str,
    ) -> UnderlyingBenchmarkAssignmentModel:
        await self._require_underlying(workspace_id, underlying_id)
        await self._require_reference(workspace_id, market_reference_id)
        await self._ensure_no_overlap(
            UnderlyingBenchmarkAssignmentModel,
            workspace_id,
            valid_from,
            valid_to,
            UnderlyingBenchmarkAssignmentModel.underlying_id == underlying_id,
            UnderlyingBenchmarkAssignmentModel.role == role.value,
            label="underlying benchmark assignment",
        )
        value = UnderlyingBenchmarkAssignmentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            market_reference_id=market_reference_id,
            role=role.value,
            valid_from=valid_from,
            valid_to=valid_to,
            source=source.strip(),
            source_reference=self._clean(source_reference),
            quality_status=quality_status,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def assign_underlying_sector(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        sector_id: UUID,
        valid_from: date,
        valid_to: date | None,
        source: str,
        source_reference: str | None,
        quality_status: str,
    ) -> UnderlyingSectorAssignmentModel:
        await self._require_underlying(workspace_id, underlying_id)
        await self._require_sector(workspace_id, sector_id)
        await self._ensure_no_overlap(
            UnderlyingSectorAssignmentModel,
            workspace_id,
            valid_from,
            valid_to,
            UnderlyingSectorAssignmentModel.underlying_id == underlying_id,
            label="underlying sector assignment",
        )
        value = UnderlyingSectorAssignmentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            sector_id=sector_id,
            valid_from=valid_from,
            valid_to=valid_to,
            source=source.strip(),
            source_reference=self._clean(source_reference),
            quality_status=quality_status,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def assign_sector_reference(
        self,
        *,
        workspace_id: UUID,
        sector_id: UUID,
        market_reference_id: UUID,
        valid_from: date,
        valid_to: date | None,
        source: str,
        quality_status: str,
    ) -> SectorReferenceAssignmentModel:
        await self._require_sector(workspace_id, sector_id)
        reference = await self._require_reference(workspace_id, market_reference_id)
        if reference.reference_type != MarketReferenceType.SECTOR_INDEX.value:
            raise ValueError("sector reference must have reference_type SECTOR_INDEX")
        await self._ensure_no_overlap(
            SectorReferenceAssignmentModel,
            workspace_id,
            valid_from,
            valid_to,
            SectorReferenceAssignmentModel.sector_id == sector_id,
            label="sector reference assignment",
        )
        value = SectorReferenceAssignmentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            sector_id=sector_id,
            market_reference_id=market_reference_id,
            valid_from=valid_from,
            valid_to=valid_to,
            source=source.strip(),
            quality_status=quality_status,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def create_sector_reference(
        self,
        *,
        workspace_id: UUID,
        code: str,
        name: str,
        region: str,
        reference_version: str,
    ) -> MarketReferenceModel:
        normalized = code.strip().upper()
        existing = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.code == normalized,
            )
        )
        if existing is not None:
            raise ValueError("market reference code already exists")
        value = MarketReferenceModel(
            id=uuid4(),
            workspace_id=workspace_id,
            code=normalized,
            name=name.strip(),
            reference_type=MarketReferenceType.SECTOR_INDEX.value,
            region=region.strip().upper(),
            role=BenchmarkRole.SECTOR_REFERENCE.value,
            reference_version=reference_version.strip(),
            active=True,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.commit()
        return value

    async def _require_reference(
        self, workspace_id: UUID, reference_id: UUID
    ) -> MarketReferenceModel:
        value = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.id == reference_id,
                MarketReferenceModel.active.is_(True),
            )
        )
        if value is None:
            raise ValueError("market reference not found or inactive")
        return value

    async def _require_sector(self, workspace_id: UUID, sector_id: UUID) -> SectorModel:
        value = await self._session.scalar(
            select(SectorModel).where(
                SectorModel.workspace_id == workspace_id,
                SectorModel.id == sector_id,
                SectorModel.active.is_(True),
            )
        )
        if value is None:
            raise ValueError("sector not found or inactive")
        return value

    async def _require_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> UnderlyingModel:
        value = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.id == underlying_id,
            )
        )
        if value is None:
            raise ValueError("underlying not found in workspace")
        return value

    async def _ensure_no_overlap(
        self,
        model: type[Any],
        workspace_id: UUID,
        valid_from: date,
        valid_to: date | None,
        *predicates: ColumnElement[bool],
        label: str,
    ) -> None:
        if valid_to is not None and valid_to < valid_from:
            raise ValueError("valid_to must not precede valid_from")
        new_end = valid_to or date.max
        overlap = await self._session.scalar(
            select(model.id)
            .where(
                model.workspace_id == workspace_id,
                *predicates,
                model.valid_from <= new_end,
                or_(model.valid_to.is_(None), model.valid_to >= valid_from),
            )
            .limit(1)
        )
        if overlap is not None:
            raise ValueError(f"overlapping {label} already exists")

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
