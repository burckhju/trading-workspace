"""Workspace-scoped dynamic issuer batches; each mapping still requires exact proof."""

import asyncio
from time import monotonic
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from app.core.config.jpmorgan import JPMorganSettings
from app.core.config.morganstanley import MorganStanleySettings
from app.database import DatabaseManager
from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.persistence.quote_identity import QuoteIdentity, verified_identity
from app.features.product.persistence.models import WarrantListingModel, WarrantModel


async def read_bindings(
    database: DatabaseManager, workspace_id: UUID, provider: MarketDataProvider
) -> dict[str, str]:
    async with database.session_context() as session:
        rows = (
            await session.execute(
                select(
                    WarrantListingModel,
                    WarrantModel,
                    TradingVenueModel,
                    WarrantProviderMappingModel,
                )
                .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                .join(
                    TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id
                )
                .join(
                    WarrantProviderMappingModel,
                    WarrantProviderMappingModel.warrant_listing_id == WarrantListingModel.id,
                )
                .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
                .join(
                    CurrencyModel, CurrencyModel.code == WarrantListingModel.quotation_currency_code
                )
                .where(
                    WarrantProviderMappingModel.provider == provider,
                    WarrantProviderMappingModel.workspace_id == workspace_id,
                    IssuerModel.is_active.is_(True),
                    CurrencyModel.is_active.is_(True),
                )
                .order_by(WarrantModel.isin)
            )
        ).all()
    bindings: dict[str, str] = {}
    conflicts = set()
    for listing, warrant, venue, mapping in rows:
        identity = verified_identity(workspace_id, listing, warrant, venue, provider, mapping)
        if identity is not None and identity.stream_id:
            if identity.isin in bindings and bindings[identity.isin] != identity.stream_id:
                conflicts.add(identity.isin)
            bindings[identity.isin] = identity.stream_id
    return {isin: stream for isin, stream in bindings.items() if isin not in conflicts}


class IssuerPriceIdentity(Protocol):
    @property
    def isin(self) -> str: ...

    @property
    def wkn(self) -> str | None: ...

    @property
    def currency(self) -> str: ...


type BatchKey = tuple[UUID, tuple[tuple[str, str], ...]]


class BatchFetcher[Item](Protocol):
    async def __call__(
        self, timeout_seconds: float, *, instruments: dict[str, str]
    ) -> dict[str, Item]: ...


class IssuerBatches[Item]:
    """Serialized batches, at most one network start per cache interval and provider.

    Cache keys contain workspace and all stream bindings. New registration can
    invalidate the registry immediately, but does not remove the network budget.
    Missing products never borrow fields from a preceding batch.
    """

    def __init__(
        self,
        database: DatabaseManager,
        provider: MarketDataProvider,
        settings: JPMorganSettings | MorganStanleySettings,
        fetcher: BatchFetcher[Item],
    ) -> None:
        self.database, self.provider, self.settings, self.fetcher = (
            database,
            provider,
            settings,
            fetcher,
        )
        self.lock = asyncio.Lock()
        self.registry_workspace: UUID | None = None
        self.bindings: dict[str, str] = {}
        self.registry_expires = 0.0
        self.next_fetch = 0.0
        self.batches: dict[BatchKey, tuple[float, dict[str, Item], str | None]] = {}
        self.last_fetched: dict[BatchKey, float] = {}

    def invalidate_routes(self) -> None:
        self.registry_expires = 0.0

    async def get(
        self, workspace_id: UUID, identity: QuoteIdentity
    ) -> tuple[Item | None, str | None, bool]:
        async with self.lock:
            now = monotonic()
            if now >= self.registry_expires or workspace_id != self.registry_workspace:
                self.bindings = await read_bindings(self.database, workspace_id, self.provider)
                self.registry_workspace = workspace_id
                self.registry_expires = monotonic() + self.settings.cache_seconds
            if self.bindings.get(identity.isin) != identity.stream_id:
                raise ValueError(f"{self.provider.value}_VERIFIED_MAPPING_REQUIRED")
            ordered = sorted(self.bindings.items())
            index = next(i for i, (isin, _) in enumerate(ordered) if isin == identity.isin)
            group = tuple(ordered[(index // 64) * 64 : (index // 64 + 1) * 64])
            key = (workspace_id, group)
            self.batches = {k: v for k, v in self.batches.items() if v[0] > now}
            if key in self.batches:
                _, cached_items, cached_error = self.batches[key]
                return cached_items.get(identity.isin), cached_error, True
            if now < self.next_fetch:
                # Background refresh tries again; API calls do not bypass the shared budget.
                raise ValueError(f"{self.provider.value}_BATCH_COOLDOWN")
            groups = [tuple(ordered[i : i + 64]) for i in range(0, len(ordered), 64)]
            selected = min(groups, key=lambda g: self.last_fetched.get((workspace_id, g), -1.0))
            fetch_key = (workspace_id, selected)
            self.last_fetched = {
                k: v
                for k, v in self.last_fetched.items()
                if k[0] == workspace_id and k[1] in groups
            }
            self.last_fetched[fetch_key] = now
            self.next_fetch = now + self.settings.cache_seconds
            error: str | None = None
            items: dict[str, Item] = {}
            try:
                items = await self.fetcher(
                    self.settings.timeout_seconds, instruments=dict(selected)
                )
            except Exception as exc:
                import re

                code = str(exc)
                error = (
                    code
                    if re.fullmatch(self.provider.value + r"_[A-Z_]{1,70}", code)
                    else f"{self.provider.value}_STREAM_FAILURE"
                )
            self.batches[fetch_key] = (monotonic() + self.settings.cache_seconds, items, error)
            if fetch_key != key:
                raise ValueError(f"{self.provider.value}_BATCH_COOLDOWN")
            return items.get(identity.isin), error, False
