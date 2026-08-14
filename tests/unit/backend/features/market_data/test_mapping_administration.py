from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VenueReconciliationStatus,
)

NOW = datetime(2026, 8, 5, 12, 30, tzinfo=UTC)


class MappingRepo:
    def __init__(self) -> None:
        self.value = None
        self.flushed = False
        self.listing_venues = {}
        self.exchange_venues = {}

    async def find_for_listing(self, *args):
        return self.value

    async def get(self, workspace_id: UUID, mapping_id: UUID):
        return self.value if self.value and self.value.id == mapping_id else None

    async def add(self, value):
        self.value = value

    async def list_all(self, workspace_id: UUID, provider=None):
        return [self.value] if self.value else []

    async def get_listing_venue_id(self, workspace_id: UUID, listing_id: UUID):
        return self.listing_venues.get(listing_id)

    async def list_active_venue_ids_for_exchange(
        self, workspace_id: UUID, provider, provider_exchange_code: str
    ):
        return self.exchange_venues.get(provider_exchange_code.strip().upper(), [])

    async def flush(self):
        self.flushed = True


class AuditRepo:
    def __init__(self) -> None:
        self.events = []

    async def append(self, value):
        self.events.append(value)


class Uow:
    def __init__(self) -> None:
        self.mappings = MappingRepo()
        self.audit_events = AuditRepo()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        return None


def command(workspace_id: UUID, listing_id: UUID) -> MappingCommand:
    return MappingCommand(
        workspace_id,
        listing_id,
        MarketDataProvider.EODHD,
        "sap",
        "xetra",
        "admin",
        "Administrator",
    )


@pytest.mark.asyncio
async def test_create_mapping_is_disabled_and_audited() -> None:
    uow = Uow()
    service = ProviderMappingAdministrationService(uow, now=lambda: NOW, id_factory=uuid4)
    value = await service.create_or_update(command(uuid4(), uuid4()))
    assert value.status is MappingStatus.DISABLED
    assert value.provider_symbol == "SAP"
    assert uow.committed and uow.mappings.flushed
    assert len(uow.audit_events.events) == 1


@pytest.mark.asyncio
async def test_validate_activates_mapping_and_records_validation_time() -> None:
    uow = Uow()
    service = ProviderMappingAdministrationService(uow, now=lambda: NOW, id_factory=uuid4)
    created = await service.create_or_update(command(uuid4(), uuid4()))
    uow.committed = False
    validated = await service.validate(
        created.workspace_id, created.id, actor_id="admin", actor_name="Administrator"
    )
    assert validated.status is MappingStatus.ACTIVE
    assert validated.validated_at == NOW
    assert uow.committed
    assert len(uow.audit_events.events) == 2


@pytest.mark.asyncio
async def test_disable_keeps_mapping_history() -> None:
    uow = Uow()
    service = ProviderMappingAdministrationService(uow, now=lambda: NOW, id_factory=uuid4)
    created = await service.create_or_update(command(uuid4(), uuid4()))
    await service.validate(
        created.workspace_id, created.id, actor_id=None, actor_name="Administrator"
    )
    disabled = await service.set_enabled(
        created.workspace_id,
        created.id,
        enabled=False,
        actor_id=None,
        actor_name="Administrator",
    )
    assert disabled.status is MappingStatus.DISABLED
    assert disabled.id == created.id
    assert len(uow.audit_events.events) == 3


class InvalidResolver:
    async def validate_mapping(self, mapping):
        from app.features.market_data.service.types import MappingValidationResult

        return MappingValidationResult(
            mapping_id=mapping.id,
            provider=mapping.provider,
            status=MappingStatus.INVALID,
            validated_at=NOW,
            message="No exact provider match",
        )


@pytest.mark.asyncio
async def test_technical_validation_failure_keeps_mapping_inactive() -> None:
    uow = Uow()
    service = ProviderMappingAdministrationService(
        uow, now=lambda: NOW, id_factory=uuid4, resolver=InvalidResolver()
    )
    created = await service.create_or_update(command(uuid4(), uuid4()))
    validated = await service.validate(
        created.workspace_id, created.id, actor_id="admin", actor_name="Administrator"
    )
    assert validated.status is MappingStatus.INVALID
    assert validated.validation_message == "No exact provider match"


@pytest.mark.asyncio
async def test_venue_reconciliation_matches_existing_active_mapping_evidence() -> None:
    uow = Uow()
    workspace_id = uuid4()
    listing_id = uuid4()
    venue_id = uuid4()
    uow.mappings.listing_venues = {listing_id: venue_id}
    uow.mappings.exchange_venues = {"XETRA": [venue_id]}
    service = ProviderVenueReconciliationService(uow)

    result = await service.reconcile(
        workspace_id,
        listing_id,
        MarketDataProvider.EODHD,
        "xetra",
    )

    assert result.status is VenueReconciliationStatus.MATCHED
    assert result.listing_venue_id == venue_id
    assert result.evidence_venue_ids == (venue_id,)


@pytest.mark.asyncio
async def test_venue_reconciliation_does_not_guess_when_evidence_is_ambiguous() -> None:
    uow = Uow()
    workspace_id = uuid4()
    listing_id = uuid4()
    venue_id = uuid4()
    uow.mappings.listing_venues = {listing_id: venue_id}
    uow.mappings.exchange_venues = {"XETRA": [uuid4(), uuid4()]}
    service = ProviderVenueReconciliationService(uow)

    result = await service.reconcile(
        workspace_id,
        listing_id,
        MarketDataProvider.EODHD,
        "XETRA",
    )

    assert result.status is VenueReconciliationStatus.AMBIGUOUS


@pytest.mark.asyncio
async def test_validation_blocks_only_clear_venue_conflict() -> None:
    uow = Uow()
    workspace_id = uuid4()
    listing_id = uuid4()
    listing_venue_id = uuid4()
    uow.mappings.listing_venues = {listing_id: listing_venue_id}
    uow.mappings.exchange_venues = {"XETRA": [uuid4()]}
    reconciliation = ProviderVenueReconciliationService(uow)
    service = ProviderMappingAdministrationService(
        uow,
        now=lambda: NOW,
        id_factory=uuid4,
        venue_reconciliation=reconciliation,
    )
    created = await service.create_or_update(command(workspace_id, listing_id))

    validated = await service.validate(
        workspace_id,
        created.id,
        actor_id="admin",
        actor_name="Administrator",
    )

    assert validated.status is MappingStatus.INVALID
    assert validated.validation_message == (
        "Provider exchange code conflicts with the listing trading venue"
    )


@pytest.mark.asyncio
async def test_reconcile_mapping_uses_persisted_mapping_context() -> None:
    uow = Uow()
    workspace_id = uuid4()
    listing_id = uuid4()
    venue_id = uuid4()
    mapping_service = ProviderMappingAdministrationService(uow, now=lambda: NOW, id_factory=uuid4)
    created = await mapping_service.create_or_update(command(workspace_id, listing_id))
    uow.mappings.listing_venues = {listing_id: venue_id}
    uow.mappings.exchange_venues = {"XETRA": [venue_id]}

    result = await ProviderVenueReconciliationService(uow).reconcile_mapping(
        workspace_id, created.id
    )

    assert result.status is VenueReconciliationStatus.MATCHED
    assert result.listing_venue_id == venue_id
