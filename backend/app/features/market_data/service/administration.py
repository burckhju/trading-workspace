"""Administrative application services for provider mappings and status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.market.domain.enums import (
    ActorType,
    AggregateType,
    ChangeType,
    DataOrigin,
)
from app.features.market.persistence.models import AuditEventModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.persistence.mapping import (
    mapping_to_domain,
    mapping_to_model,
)
from app.features.market_data.service.contracts import ProviderInstrumentResolver
from app.features.market_data.service.errors import MarketDataNotFoundError
from app.features.market_data.service.unit_of_work import MarketDataUnitOfWork
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VenueReconciliationStatus,
)


@dataclass(frozen=True, slots=True)
class MappingCommand:
    """Create or replace one provider-symbol assignment for a listing."""

    workspace_id: UUID
    listing_id: UUID
    provider: MarketDataProvider
    provider_symbol: str
    provider_exchange_code: str
    actor_id: str | None
    actor_name: str


class ProviderMappingAdministrationService:
    """Manage provider mappings without changing listing master data."""

    def __init__(
        self,
        uow: MarketDataUnitOfWork,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        id_factory: Callable[[], UUID] = uuid4,
        resolver: ProviderInstrumentResolver | None = None,
        venue_reconciliation: ProviderVenueReconciliationService | None = None,
    ) -> None:
        self._uow = uow
        self._now = now
        self._id_factory = id_factory
        self._resolver = resolver
        self._venue_reconciliation = venue_reconciliation

    async def list_mappings(self, workspace_id: UUID) -> tuple[ProviderInstrumentMapping, ...]:
        """Return all mappings for one workspace."""
        async with self._uow:
            rows = await self._uow.mappings.list_all(workspace_id)
            return tuple(mapping_to_domain(row) for row in rows)

    async def create_or_update(self, command: MappingCommand) -> ProviderInstrumentMapping:
        """Create a disabled mapping or update its symbol data idempotently."""
        async with self._uow:
            existing = await self._uow.mappings.find_for_listing(
                command.workspace_id, command.listing_id, command.provider
            )
            now = self._now()
            if existing is None:
                value = ProviderInstrumentMapping(
                    id=self._id_factory(),
                    workspace_id=command.workspace_id,
                    listing_id=command.listing_id,
                    provider=command.provider,
                    provider_symbol=command.provider_symbol,
                    provider_exchange_code=command.provider_exchange_code,
                    status=MappingStatus.DISABLED,
                    validated_at=None,
                    validation_message="Awaiting explicit validation",
                    created_at=now,
                    updated_at=now,
                    version=1,
                )
                model = mapping_to_model(value)
                await self._uow.mappings.add(model)
                await self._audit(value, command, ChangeType.CREATED, None, 1, {})
            else:
                before = mapping_to_domain(existing)
                existing.provider_symbol = command.provider_symbol.strip().upper()
                existing.provider_exchange_code = command.provider_exchange_code.strip().upper()
                existing.status = MappingStatus.DISABLED
                existing.validated_at = None
                existing.validation_message = "Awaiting explicit validation"
                existing.updated_at = now
                existing.version += 1
                value = mapping_to_domain(existing)
                await self._audit(
                    value,
                    command,
                    ChangeType.UPDATED,
                    before.version,
                    value.version,
                    self._diff(before, value),
                )
            await self._uow.mappings.flush()
            await self._uow.commit()
            return value

    async def validate(
        self,
        workspace_id: UUID,
        mapping_id: UUID,
        *,
        actor_id: str | None,
        actor_name: str,
    ) -> ProviderInstrumentMapping:
        """Validate mapping syntax and activate it explicitly."""
        async with self._uow:
            model = await self._uow.mappings.get(workspace_id, mapping_id)
            if model is None:
                raise MarketDataNotFoundError("Provider mapping not found")
            before = mapping_to_domain(model)
            validation = await self._resolver.validate_mapping(before) if self._resolver else None
            now = validation.validated_at if validation is not None else self._now()
            if validation is not None and validation.status is not MappingStatus.ACTIVE:
                model.status = MappingStatus.INVALID
                model.validated_at = now
                model.validation_message = validation.message or "Technical validation failed"
                model.updated_at = now
                model.version += 1
                value = mapping_to_domain(model)
                command = MappingCommand(
                    workspace_id,
                    model.listing_id,
                    model.provider,
                    model.provider_symbol,
                    model.provider_exchange_code,
                    actor_id,
                    actor_name,
                )
                await self._audit(
                    value,
                    command,
                    ChangeType.UPDATED,
                    before.version,
                    value.version,
                    self._diff(before, value),
                )
                await self._uow.mappings.flush()
                await self._uow.commit()
                return value

            if self._venue_reconciliation is not None:
                reconciliation = await self._venue_reconciliation.reconcile(
                    workspace_id,
                    model.listing_id,
                    model.provider,
                    model.provider_exchange_code,
                )
                if reconciliation.status is VenueReconciliationStatus.CONFLICT:
                    model.status = MappingStatus.INVALID
                    model.validated_at = now
                    model.validation_message = (
                        "Provider exchange code conflicts with the listing trading venue"
                    )
                    model.updated_at = now
                    model.version += 1
                    value = mapping_to_domain(model)
                    command = MappingCommand(
                        workspace_id,
                        model.listing_id,
                        model.provider,
                        model.provider_symbol,
                        model.provider_exchange_code,
                        actor_id,
                        actor_name,
                    )
                    await self._audit(
                        value,
                        command,
                        ChangeType.UPDATED,
                        before.version,
                        value.version,
                        self._diff(before, value),
                    )
                    await self._uow.mappings.flush()
                    await self._uow.commit()
                    return value

            model.status = MappingStatus.ACTIVE
            model.validated_at = now
            model.validation_message = (
                validation.message
                if validation is not None
                else "Validated by administrative review"
            )
            model.updated_at = now
            model.version += 1
            value = mapping_to_domain(model)
            command = MappingCommand(
                workspace_id,
                model.listing_id,
                model.provider,
                model.provider_symbol,
                model.provider_exchange_code,
                actor_id,
                actor_name,
            )
            await self._audit(
                value,
                command,
                ChangeType.ACTIVATED,
                before.version,
                value.version,
                self._diff(before, value),
            )
            await self._uow.mappings.flush()
            await self._uow.commit()
            return value

    async def set_enabled(
        self,
        workspace_id: UUID,
        mapping_id: UUID,
        *,
        enabled: bool,
        actor_id: str | None,
        actor_name: str,
    ) -> ProviderInstrumentMapping:
        """Activate a validated mapping or disable it without deleting history."""
        async with self._uow:
            model = await self._uow.mappings.get(workspace_id, mapping_id)
            if model is None:
                raise MarketDataNotFoundError("Provider mapping not found")
            before = mapping_to_domain(model)
            now = self._now()
            if enabled:
                model.status = MappingStatus.ACTIVE
                model.validated_at = model.validated_at or now
                model.validation_message = "Activated administratively"
                change = ChangeType.REACTIVATED
            else:
                model.status = MappingStatus.DISABLED
                model.validation_message = "Disabled administratively"
                change = ChangeType.DEACTIVATED
            model.updated_at = now
            model.version += 1
            value = mapping_to_domain(model)
            command = MappingCommand(
                workspace_id,
                model.listing_id,
                model.provider,
                model.provider_symbol,
                model.provider_exchange_code,
                actor_id,
                actor_name,
            )
            await self._audit(
                value,
                command,
                change,
                before.version,
                value.version,
                self._diff(before, value),
            )
            await self._uow.mappings.flush()
            await self._uow.commit()
            return value

    async def _audit(
        self,
        value: ProviderInstrumentMapping,
        command: MappingCommand,
        change: ChangeType,
        before: int | None,
        after: int,
        fields: dict[str, dict[str, str | None]],
    ) -> None:
        await self._uow.audit_events.append(
            AuditEventModel(
                id=self._id_factory(),
                workspace_id=value.workspace_id,
                aggregate_type=AggregateType.PROVIDER_MAPPING,
                aggregate_id=value.id,
                occurred_at=value.updated_at,
                actor_type=ActorType.SYSTEM_USER,
                actor_id=command.actor_id,
                actor_display_name=command.actor_name,
                data_origin=DataOrigin.MANUAL,
                change_type=change,
                version_before=before,
                version_after=after,
                field_changes=fields,
            )
        )

    @staticmethod
    def _diff(
        before: ProviderInstrumentMapping, after: ProviderInstrumentMapping
    ) -> dict[str, dict[str, str | None]]:
        ignored = {"created_at", "updated_at", "version"}
        result: dict[str, dict[str, str | None]] = {}
        for key, old in asdict(before).items():
            if key in ignored:
                continue
            new = getattr(after, key)
            if old != new:
                result[key] = {
                    "before": str(old) if old is not None else None,
                    "after": str(new) if new is not None else None,
                }
        return result
