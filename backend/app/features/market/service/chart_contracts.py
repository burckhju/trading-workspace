"""Read-only market identity/context contracts; visual selection never writes them."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ChartIdentity:
    key: str
    name: str
    instrument_id: UUID | None
    instrument_type: str
    reference_id: UUID | None = None
    reference_code: str | None = None
    underlying_id: UUID | None = None
    listing_id: UUID | None = None
    isin: str | None = None
    ticker: str | None = None
    mic: str | None = None
    currency: str | None = None
    return_basis: str = "UNKNOWN"
    basis_source: str | None = None
    active: bool = True
    mapping_status: str = "MISSING"
    provider_identity: str | None = None
    mapping_id: UUID | None = None
    mapping_version: int | None = None
    setup_url: str = "/top-down-admin"


@dataclass(frozen=True)
class SectorChartContext:
    id: UUID
    code: str
    name: str
    classification_system: str
    classification_version: str
    active: bool
    reference: ChartIdentity | None
    proxy: ChartIdentity | None
    status: str
    setup_url: str


@dataclass(frozen=True)
class UnderlyingChartContext:
    underlying_id: UUID
    subject: ChartIdentity | None
    market: ChartIdentity | None
    sector: ChartIdentity | None
    issues: tuple[str, ...]
    assignment_date: date


class ChartContextReader(Protocol):
    async def resolve(self, workspace_id: UUID, key: str) -> ChartIdentity: ...

    async def references(self, workspace_id: UUID) -> tuple[ChartIdentity, ...]: ...

    async def reference_proxies(
        self, workspace_id: UUID, as_of: date
    ) -> tuple[ChartIdentity, ...]: ...

    async def sectors(self, workspace_id: UUID, as_of: date) -> tuple[SectorChartContext, ...]: ...

    async def underlying(
        self, workspace_id: UUID, underlying_id: UUID, as_of: date
    ) -> UnderlyingChartContext: ...
