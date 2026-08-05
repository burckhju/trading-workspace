"""Application service orchestration for FT-001 Basiswertverwaltung."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.features.market.domain.entities import (
    Listing,
    Underlying,
    determine_quality_status,
    ensure_expected_version,
)
from app.features.market.domain.enums import (
    ActorType,
    AggregateType,
    ChangeType,
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
)
from app.features.market.domain.normalization import normalize_isin, normalize_ticker, normalize_wkn
from app.features.market.persistence.models import AuditEventModel, ListingModel, UnderlyingModel
from app.features.market.service.errors import (
    CurrencyNotFound,
    DuplicateIsin,
    DuplicateMarketTicker,
    DuplicateWkn,
    InactiveReferenceData,
    TradingVenueNotFound,
    UnderlyingDeleteReferenced,
    UnderlyingNotFound,
    WorkspaceNotFound,
)
from app.features.market.service.mapping import apply_underlying, listing_to_domain, underlying_to_domain
from app.features.market.service.types import (
    ChangeUnderlyingStatus,
    CreateUnderlying,
    DeleteUnderlying,
    SearchUnderlyings,
    AuditEventView,
    UsageSummary,
    UpdateUnderlying,
)
from app.features.market.service.unit_of_work import MarketUnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class UnderlyingService:
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

    async def create(self, command: CreateUnderlying) -> UnderlyingModel:
        now = self._clock()
        underlying_id = self._id_factory()
        listing_id = self._id_factory()
        listing = Listing(
            id=listing_id,
            workspace_id=command.workspace_id,
            underlying_id=underlying_id,
            trading_venue_id=command.primary_listing.trading_venue_id,
            ticker=command.primary_listing.ticker,
            currency_code=command.primary_listing.currency_code,
            lifecycle_status=LifecycleStatus.ACTIVE,
            is_primary=command.primary_listing.is_primary,
            version=1,
            created_at=now,
            updated_at=now,
        )
        quality = determine_quality_status(name=command.name, listings=(listing,))
        underlying = Underlying(
            id=underlying_id,
            workspace_id=command.workspace_id,
            type=command.type,
            name=command.name,
            isin=command.isin,
            wkn=command.wkn,
            lifecycle_status=LifecycleStatus.ACTIVE,
            quality_status=quality,
            version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._ensure_workspace(command.workspace_id)
            await self._ensure_reference_data(listing.trading_venue_id, listing.currency_code)
            await self._ensure_unique_underlying(command.workspace_id, underlying.isin, underlying.wkn)
            await self._ensure_unique_listing(
                command.workspace_id, listing.trading_venue_id, listing.ticker
            )
            underlying_model = UnderlyingModel(**asdict(underlying))
            listing_model = ListingModel(**asdict(listing))
            await self._uow.underlyings.add(underlying_model)
            await self._uow.listings.add(listing_model)
            await self._append_audit(
                workspace_id=command.workspace_id,
                aggregate_type=AggregateType.UNDERLYING,
                aggregate_id=underlying.id,
                actor_id=command.actor.id,
                actor_name=command.actor.display_name,
                change_type=ChangeType.CREATED,
                version_before=None,
                version_after=1,
                field_changes=self._created_changes(underlying),
                occurred_at=now,
            )
            await self._append_audit(
                workspace_id=command.workspace_id,
                aggregate_type=AggregateType.LISTING,
                aggregate_id=listing.id,
                actor_id=command.actor.id,
                actor_name=command.actor.display_name,
                change_type=ChangeType.CREATED,
                version_before=None,
                version_after=1,
                field_changes=self._created_changes(listing),
                occurred_at=now,
            )
            await self._uow.underlyings.flush()
            await self._uow.listings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return underlying_model

    async def update(self, command: UpdateUnderlying) -> UnderlyingModel:
        async with self._uow:
            model = await self._require_underlying(command.workspace_id, command.underlying_id)
            current = underlying_to_domain(model)
            ensure_expected_version(command.expected_version, current.version)
            updated = current.with_master_data(
                now=self._clock(), name=command.name, isin=command.isin, wkn=command.wkn
            )
            if updated is current:
                return model
            await self._ensure_unique_underlying(
                command.workspace_id,
                updated.isin,
                updated.wkn,
                exclude_id=current.id,
            )
            changes = self._diff(current, updated)
            apply_underlying(model, updated)
            await self._append_audit(
                workspace_id=command.workspace_id,
                aggregate_type=AggregateType.UNDERLYING,
                aggregate_id=current.id,
                actor_id=command.actor.id,
                actor_name=command.actor.display_name,
                change_type=ChangeType.UPDATED,
                version_before=current.version,
                version_after=updated.version,
                field_changes=changes,
                occurred_at=updated.updated_at,
            )
            await self._uow.underlyings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def deactivate(self, command: ChangeUnderlyingStatus) -> UnderlyingModel:
        return await self._change_status(command, activate=False)

    async def reactivate(self, command: ChangeUnderlyingStatus) -> UnderlyingModel:
        return await self._change_status(command, activate=True)

    async def verify(self, command: ChangeUnderlyingStatus) -> UnderlyingModel:
        async with self._uow:
            model = await self._require_underlying(command.workspace_id, command.underlying_id)
            current = underlying_to_domain(model)
            ensure_expected_version(command.expected_version, current.version)
            listings = tuple(
                listing_to_domain(item)
                for item in await self._uow.listings.list_for_underlying(
                    command.workspace_id, command.underlying_id
                )
            )
            updated = current.verify(now=self._clock(), listings=listings)
            if updated is current:
                return model
            apply_underlying(model, updated)
            await self._append_change(current, updated, command.actor.id, command.actor.display_name)
            await self._uow.underlyings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def delete(self, command: DeleteUnderlying) -> None:
        async with self._uow:
            model = await self._require_underlying(command.workspace_id, command.underlying_id)
            current = underlying_to_domain(model)
            ensure_expected_version(command.expected_version, current.version)
            references = tuple(
                await self._uow.usages.list_for_underlying(
                    command.workspace_id, command.underlying_id
                )
            )
            if references:
                raise UnderlyingDeleteReferenced(
                    "Referenced underlying cannot be deleted", references=references
                )
            listings = tuple(
                await self._uow.listings.list_for_underlying(
                    command.workspace_id, command.underlying_id
                )
            )
            now = self._clock()
            for listing in listings:
                await self._append_audit(
                    workspace_id=command.workspace_id,
                    aggregate_type=AggregateType.LISTING,
                    aggregate_id=listing.id,
                    actor_id=command.actor.id,
                    actor_name=command.actor.display_name,
                    change_type=ChangeType.DELETED,
                    version_before=listing.version,
                    version_after=None,
                    field_changes=self._deleted_changes(listing_to_domain(listing)),
                    occurred_at=now,
                )
            await self._append_audit(
                workspace_id=command.workspace_id,
                aggregate_type=AggregateType.UNDERLYING,
                aggregate_id=current.id,
                actor_id=command.actor.id,
                actor_name=command.actor.display_name,
                change_type=ChangeType.DELETED,
                version_before=current.version,
                version_after=None,
                field_changes=self._deleted_changes(current),
                occurred_at=now,
            )
            await self._uow.underlyings.delete(model)
            await self._uow.audit_events.flush()
            await self._uow.commit()

    async def get(self, workspace_id: UUID, underlying_id: UUID) -> UnderlyingModel:
        async with self._uow:
            return await self._require_underlying(workspace_id, underlying_id, with_listings=True)

    async def search(self, query: SearchUnderlyings) -> tuple[Sequence[UnderlyingModel], int]:
        if query.offset < 0 or query.limit < 1 or query.limit > 200:
            raise ValueError("Pagination must use offset >= 0 and 1 <= limit <= 200")
        async with self._uow:
            items = await self._uow.underlyings.search(
                query.workspace_id,
                query.query,
                query.lifecycle_status,
                query.trading_venue_id,
                query.currency_code,
                offset=query.offset,
                limit=query.limit,
            )
            total = await self._uow.underlyings.count_search(
                query.workspace_id, query.query, query.lifecycle_status, query.trading_venue_id, query.currency_code
            )
            return items, total


    async def audit_history(
        self, workspace_id: UUID, underlying_id: UUID, *, offset: int, limit: int
    ) -> tuple[tuple[AuditEventView, ...], int]:
        async with self._uow:
            await self._require_underlying(workspace_id, underlying_id)
            listings = await self._uow.listings.list_for_underlying(workspace_id, underlying_id)
            listing_ids = tuple(item.id for item in listings)
            events = await self._uow.audit_events.list_for_underlying_history(
                workspace_id, underlying_id, listing_ids, offset=offset, limit=limit
            )
            total = await self._uow.audit_events.count_for_underlying_history(
                workspace_id, underlying_id, listing_ids
            )
            return tuple(AuditEventView(
                id=e.id, aggregate_type=e.aggregate_type.value, aggregate_id=e.aggregate_id,
                occurred_at=e.occurred_at, actor_display_name=e.actor_display_name,
                change_type=e.change_type.value, version_before=e.version_before,
                version_after=e.version_after, field_changes=e.field_changes
            ) for e in events), total

    async def usages(self, workspace_id: UUID, underlying_id: UUID) -> tuple[UsageSummary, ...]:
        async with self._uow:
            await self._require_underlying(workspace_id, underlying_id)
            references = await self._uow.usages.list_for_underlying(workspace_id, underlying_id)
            grouped: dict[str, list[UUID]] = {}
            for reference in references:
                grouped.setdefault(reference.reference_type, []).append(reference.object_id)
            return tuple(UsageSummary(kind, len(ids), tuple(ids)) for kind, ids in sorted(grouped.items()))

    async def _change_status(
        self, command: ChangeUnderlyingStatus, *, activate: bool
    ) -> UnderlyingModel:
        async with self._uow:
            model = await self._require_underlying(command.workspace_id, command.underlying_id)
            current = underlying_to_domain(model)
            ensure_expected_version(command.expected_version, current.version)
            if activate:
                listings = tuple(
                    listing_to_domain(item)
                    for item in await self._uow.listings.list_for_underlying(
                        command.workspace_id, command.underlying_id
                    )
                )
                updated = current.reactivate(now=self._clock(), listings=listings)
                change_type = ChangeType.REACTIVATED
            else:
                updated = current.deactivate(now=self._clock())
                change_type = ChangeType.DEACTIVATED
            if updated is current:
                return model
            apply_underlying(model, updated)
            await self._append_audit(
                workspace_id=command.workspace_id,
                aggregate_type=AggregateType.UNDERLYING,
                aggregate_id=current.id,
                actor_id=command.actor.id,
                actor_name=command.actor.display_name,
                change_type=change_type,
                version_before=current.version,
                version_after=updated.version,
                field_changes=self._diff(current, updated),
                occurred_at=updated.updated_at,
            )
            await self._uow.underlyings.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def _ensure_workspace(self, workspace_id: UUID) -> None:
        if await self._uow.workspaces.get(workspace_id) is None:
            raise WorkspaceNotFound("Workspace does not exist", field="workspace_id")

    async def _ensure_reference_data(self, venue_id: UUID, currency_code: str) -> None:
        venue = await self._uow.reference_data.get_trading_venue(venue_id)
        if venue is None:
            raise TradingVenueNotFound("Trading venue does not exist", field="trading_venue_id")
        currency = await self._uow.reference_data.get_currency(currency_code)
        if currency is None:
            raise CurrencyNotFound("Currency does not exist", field="currency_code")
        if not venue.is_active or not currency.is_active:
            raise InactiveReferenceData("Reference data is inactive")

    async def _ensure_unique_underlying(
        self,
        workspace_id: UUID,
        isin: str | None,
        wkn: str | None,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        if isin:
            duplicate = await self._uow.underlyings.find_by_isin(workspace_id, normalize_isin(isin) or "")
            if duplicate is not None and duplicate.id != exclude_id:
                raise DuplicateIsin("ISIN already exists", field="isin")
        if wkn:
            duplicate = await self._uow.underlyings.find_by_wkn(workspace_id, normalize_wkn(wkn) or "")
            if duplicate is not None and duplicate.id != exclude_id:
                raise DuplicateWkn("WKN already exists", field="wkn")

    async def _ensure_unique_listing(
        self, workspace_id: UUID, venue_id: UUID, ticker: str, *, exclude_id: UUID | None = None
    ) -> None:
        duplicate = await self._uow.listings.find_by_venue_ticker(
            workspace_id, venue_id, normalize_ticker(ticker)
        )
        if duplicate is not None and duplicate.id != exclude_id:
            raise DuplicateMarketTicker("Ticker already exists at trading venue", field="ticker")

    async def _require_underlying(
        self, workspace_id: UUID, underlying_id: UUID, *, with_listings: bool = False
    ) -> UnderlyingModel:
        model = (
            await self._uow.underlyings.get_with_listings(workspace_id, underlying_id)
            if with_listings
            else await self._uow.underlyings.get(workspace_id, underlying_id)
        )
        if model is None:
            raise UnderlyingNotFound("Underlying does not exist")
        return model

    async def _append_change(
        self, before: Underlying, after: Underlying, actor_id: str | None, actor_name: str
    ) -> None:
        await self._append_audit(
            workspace_id=before.workspace_id,
            aggregate_type=AggregateType.UNDERLYING,
            aggregate_id=before.id,
            actor_id=actor_id,
            actor_name=actor_name,
            change_type=ChangeType.UPDATED,
            version_before=before.version,
            version_after=after.version,
            field_changes=self._diff(before, after),
            occurred_at=after.updated_at,
        )

    async def _append_audit(
        self,
        *,
        workspace_id: UUID,
        aggregate_type: AggregateType,
        aggregate_id: UUID,
        actor_id: str | None,
        actor_name: str,
        change_type: ChangeType,
        version_before: int | None,
        version_after: int | None,
        field_changes: dict[str, dict[str, Any]],
        occurred_at: datetime,
    ) -> None:
        await self._uow.audit_events.append(
            AuditEventModel(
                id=self._id_factory(),
                workspace_id=workspace_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                occurred_at=occurred_at,
                actor_type=ActorType.SYSTEM_USER,
                actor_id=actor_id,
                actor_display_name=actor_name,
                data_origin=DataOrigin.MANUAL,
                change_type=change_type,
                version_before=version_before,
                version_after=version_after,
                field_changes=field_changes,
            )
        )

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, (UUID, datetime)):
            return str(value)
        if hasattr(value, "value"):
            return value.value
        return value

    @classmethod
    def _diff(cls, before: Any, after: Any) -> dict[str, dict[str, Any]]:
        ignored = {"created_at", "updated_at", "version"}
        result: dict[str, dict[str, Any]] = {}
        for field, old in asdict(before).items():
            if field in ignored:
                continue
            new = getattr(after, field)
            if old != new:
                result[field] = {"old": cls._json_value(old), "new": cls._json_value(new)}
        return result

    @classmethod
    def _created_changes(cls, entity: Any) -> dict[str, dict[str, Any]]:
        return {
            field: {"old": None, "new": cls._json_value(value)}
            for field, value in asdict(entity).items()
            if field not in {"created_at", "updated_at"}
        }

    @classmethod
    def _deleted_changes(cls, entity: Any) -> dict[str, dict[str, Any]]:
        return {
            field: {"old": cls._json_value(value), "new": None}
            for field, value in asdict(entity).items()
            if field not in {"created_at", "updated_at"}
        }
