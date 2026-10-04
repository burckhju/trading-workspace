"""Read-only chart orchestration over public market and market-data contracts."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.time_series import (
    MAX_SERIES,
    ChartComparison,
    compare_series,
    prepare_series,
)
from app.features.market.service.chart_contracts import (
    ChartContextReader,
    ChartIdentity,
    SectorChartContext,
    UnderlyingChartContext,
)
from app.features.market_data.service.time_series import SeriesCoverage, TimeSeriesReader


@dataclass(frozen=True)
class CoveredIdentity:
    identity: ChartIdentity
    history: SeriesCoverage


@dataclass(frozen=True)
class SectorCoverage:
    context: SectorChartContext
    reference_history: SeriesCoverage
    proxy_history: SeriesCoverage


@dataclass(frozen=True)
class ChartCatalog:
    references: tuple[CoveredIdentity, ...]
    sectors: tuple[SectorCoverage, ...]
    as_of: date
    taxonomy_status: str
    proxies: tuple[CoveredIdentity, ...] = ()


class ChartService:
    def __init__(
        self,
        context: ChartContextReader,
        prices: TimeSeriesReader,
        *,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self._context = context
        self._prices = prices
        self._today = today

    def validate_dates(self, start: date | None, end: date) -> None:
        if end > self._today():
            raise ValueError("future chart dates are not supported")
        if end < date(1900, 1, 1) or (start and (start < date(1900, 1, 1) or start > end)):
            raise ValueError("invalid chart date range")

    async def series(
        self,
        workspace_id: UUID,
        keys: tuple[str, ...],
        start: date | None,
        end: date,
        field: PriceField,
    ) -> ChartComparison:
        self.validate_dates(start, end)
        if not 1 <= len(keys) <= MAX_SERIES or len(set(keys)) != len(keys):
            raise ValueError("one to four distinct series required")
        values = []
        for key in keys:
            identity = await self._context.resolve(workspace_id, key)
            rows = (
                ()
                if identity.instrument_id is None
                else await self._prices.observations(
                    workspace_id, identity.instrument_id, start or date(1900, 1, 1), end
                )
            )
            values.append(prepare_series(identity, rows, field, start, end))
        return compare_series(tuple(values), start, end, field)

    async def catalog(self, workspace_id: UUID, as_of: date) -> ChartCatalog:
        self.validate_dates(None, as_of)
        references = await self._context.references(workspace_id)
        sectors = await self._context.sectors(workspace_id, as_of)
        proxies = await self._context.reference_proxies(workspace_id, as_of)
        identities = [*references, *proxies, *(item.proxy for item in sectors if item.proxy)]
        instrument_ids = tuple({item.instrument_id for item in identities if item.instrument_id})
        coverage = await self._prices.coverage(workspace_id, instrument_ids, as_of)

        def history(identity: ChartIdentity | None) -> SeriesCoverage:
            if identity is None or identity.instrument_id is None:
                return SeriesCoverage(0, None, None)
            return coverage.get(identity.instrument_id, SeriesCoverage(0, None, None))

        return ChartCatalog(
            tuple(CoveredIdentity(item, history(item)) for item in references),
            tuple(
                SectorCoverage(item, history(item.reference), history(item.proxy))
                for item in sectors
            ),
            as_of,
            "CONFIGURED" if sectors else "NO_SECTOR_TAXONOMY",
            tuple(CoveredIdentity(item, history(item)) for item in proxies),
        )

    async def underlying(
        self, workspace_id: UUID, underlying_id: UUID, as_of: date
    ) -> UnderlyingChartContext:
        self.validate_dates(None, as_of)
        return await self._context.underlying(workspace_id, underlying_id, as_of)
