"""Listing use-case orchestration for FT-001."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.features.market.domain.entities import (
    Listing,
    ensure_expected_version,
    ensure_operational_listing_invariant,
)
from app.features.market.domain.enums import (
    ActorType,
    AggregateType,
    ChangeType,
    DataOrigin,
    LifecycleStatus,
)
from app.features.market.domain.normalization import normalize_ticker
from app.features.market.persistence.models import AuditEventModel, ListingModel
from app.features.market.service.errors import (
    CurrencyNotFound,
    DuplicateMarketTicker,
    InactiveReferenceData,
    ListingNotFound,
    TradingVenueNotFound,
    UnderlyingNotFound,
)
from app.features.market.service.mapping import apply_listing, listing_to_domain
from app.features.market.service.types import (
    AddListing,
    SetPrimaryListing,
    UpdateListing,
)
from app.features.market.service.unit_of_work import MarketUnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class ListingService:
    def __init__(
        self,
        uow: MarketUnitOfWork,
        *,
        clock: Clock = lambda: datetime.now(UTC),
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_factory = id_factory

    async def add(self, command: AddListing) -> ListingModel:
        now = self._clock()
        async with self._uow:
            underlying = await self._uow.underlyings.get(
                command.workspace_id,
                command.underlying_id,
            )
            if underlying is None:
                raise UnderlyingNotFound("Underlying does not exist")
            await self._ensure_reference_data(
                command.trading_venue_id,
                command.currency_code,
            )
            await self._ensure_unique(
                command.workspace_id,
                command.trading_venue_id,
                command.ticker,
            )
            existing = tuple(
                listing_to_domain(item)
                for item in await self._uow.listings.list_for_underlying(
                    command.workspace_id, command.underlying_id
                )
            )
            listing = Listing(
                id=self._id_factory(),
                workspace_id=command.workspace_id,
                underlying_id=command.underlying_id,
                trading_venue_id=command.trading_venue_id,
                ticker=command.ticker,
                currency_code=command.currency_code,
                lifecycle_status=LifecycleStatus.ACTIVE,
                is_primary=command.is_primary,
                version=1,
                created_at=now,
                updated_at=now,
            )
            if listing.is_primary:
                ensure_operational_listing_invariant((*existing, listing))
            model = ListingModel(**asdict(listing))
            await self._uow.listings.add(model)
            await self._audit(
                listing,
                command.actor.id,
                command.actor.display_name,
                ChangeType.CREATED,
                None,
            )
            await self._uow.listings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def update(self, command: UpdateListing) -> ListingModel:
        async with self._uow:
            model = await self._require(command.workspace_id, command.listing_id)
            current = listing_to_domain(model)
            ensure_expected_version(command.expected_version, current.version)
            venue_id = command.trading_venue_id or current.trading_venue_id
            ticker = command.ticker or current.ticker
            currency = command.currency_code or current.currency_code
            lifecycle = command.lifecycle_status or current.lifecycle_status
            await self._ensure_reference_data(venue_id, currency)
            await self._ensure_unique(command.workspace_id, venue_id, ticker, exclude_id=current.id)
            updated = current.with_changes(
                now=self._clock(),
                trading_venue_id=venue_id,
                ticker=ticker,
                currency_code=currency,
                lifecycle_status=lifecycle,
            )
            if self._same(current, updated):
                return model
            siblings = tuple(
                updated if item.id == current.id else item
                for item in (
                    listing_to_domain(candidate)
                    for candidate in await self._uow.listings.list_for_underlying(
                        command.workspace_id, current.underlying_id
                    )
                )
            )
            ensure_operational_listing_invariant(siblings)
            apply_listing(model, updated)
            await self._audit(
                updated,
                command.actor.id,
                command.actor.display_name,
                ChangeType.UPDATED,
                current,
            )
            await self._uow.listings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def set_primary(self, command: SetPrimaryListing) -> ListingModel:
        async with self._uow:
            models = list(
                await self._uow.listings.list_for_underlying(
                    command.workspace_id, command.underlying_id
                )
            )
            target_model = next((item for item in models if item.id == command.listing_id), None)
            if target_model is None:
                raise ListingNotFound("Listing does not exist")
            target = listing_to_domain(target_model)
            ensure_expected_version(command.expected_listing_version, target.version)
            if target.lifecycle_status is not LifecycleStatus.ACTIVE:
                raise ValueError("Inactive listing cannot become primary")
            now = self._clock()
            changed: list[tuple[ListingModel, Listing, Listing]] = []
            for model in models:
                before = listing_to_domain(model)
                desired = model.id == target.id
                if before.is_primary == desired:
                    continue
                after = before.with_changes(now=now, is_primary=desired)
                apply_listing(model, after)
                changed.append((model, before, after))
            ensure_operational_listing_invariant(tuple(listing_to_domain(item) for item in models))
            for _, before, after in changed:
                await self._audit(
                    after,
                    command.actor.id,
                    command.actor.display_name,
                    ChangeType.PRIMARY_CHANGED,
                    before,
                )
            if changed:
                await self._uow.listings.flush()
                await self._uow.audit_events.flush()
                await self._uow.commit()
            return target_model

    async def _require(self, workspace_id: UUID, listing_id: UUID) -> ListingModel:
        model = await self._uow.listings.get(workspace_id, listing_id)
        if model is None:
            raise ListingNotFound("Listing does not exist")
        return model

    async def _ensure_reference_data(self, venue_id: UUID, currency_code: str) -> None:
        venue = await self._uow.reference_data.get_trading_venue(venue_id)
        if venue is None:
            raise TradingVenueNotFound("Trading venue does not exist", field="trading_venue_id")
        currency = await self._uow.reference_data.get_currency(currency_code.upper())
        if currency is None:
            raise CurrencyNotFound("Currency does not exist", field="currency_code")
        if not venue.is_active or not currency.is_active:
            raise InactiveReferenceData("Reference data is inactive")

    async def _ensure_unique(
        self,
        workspace_id: UUID,
        venue_id: UUID,
        ticker: str,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        duplicate = await self._uow.listings.find_by_venue_ticker(
            workspace_id, venue_id, normalize_ticker(ticker)
        )
        if duplicate is not None and duplicate.id != exclude_id:
            raise DuplicateMarketTicker("Ticker already exists at trading venue", field="ticker")

    async def _audit(
        self,
        after: Listing,
        actor_id: str | None,
        actor_name: str,
        change_type: ChangeType,
        before: Listing | None,
    ) -> None:
        fields: dict[str, dict[str, Any]] = {}
        for key, new in asdict(after).items():
            if key in {"created_at", "updated_at"}:
                continue
            old = getattr(before, key) if before is not None else None
            if before is None or old != new:
                fields[key] = {"old": self._json(old), "new": self._json(new)}
        await self._uow.audit_events.append(
            AuditEventModel(
                id=self._id_factory(),
                workspace_id=after.workspace_id,
                aggregate_type=AggregateType.LISTING,
                aggregate_id=after.id,
                occurred_at=after.updated_at,
                actor_type=ActorType.SYSTEM_USER,
                actor_id=actor_id,
                actor_display_name=actor_name,
                data_origin=DataOrigin.MANUAL,
                change_type=change_type,
                version_before=before.version if before else None,
                version_after=after.version,
                field_changes=fields,
            )
        )

    @staticmethod
    def _json(value: Any) -> Any:
        if isinstance(value, (UUID, datetime)):
            return str(value)
        if hasattr(value, "value"):
            return value.value
        return value

    @staticmethod
    def _same(before: Listing, after: Listing) -> bool:
        return all(
            getattr(before, field) == getattr(after, field)
            for field in (
                "trading_venue_id",
                "ticker",
                "currency_code",
                "lifecycle_status",
                "is_primary",
            )
        )
