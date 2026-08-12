from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest

from app.features.market.domain.enums import LifecycleStatus, QualityStatus
from app.features.market.domain.errors import ConcurrentModification
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.market.service.errors import DuplicateIsin, UnderlyingDeleteReferenced
from app.features.market.service.listing_service import ListingService
from app.features.market.service.service import UnderlyingService
from app.features.market.service.types import (
    Actor,
    AddListing,
    ChangeUnderlyingStatus,
    CreateListing,
    CreateUnderlying,
    DeleteUnderlying,
    SearchUnderlyings,
    SetPrimaryListing,
    UpdateListing,
    UpdateUnderlying,
    UsageReference,
)

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
VENUE_ID = UUID("00000000-0000-4000-8001-000000000001")
UNDERLYING_ID = UUID("10000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("20000000-0000-4000-8000-000000000001")
AUDIT_1 = UUID("30000000-0000-4000-8000-000000000001")
AUDIT_2 = UUID("30000000-0000-4000-8000-000000000002")
ACTOR = Actor(id="user-1", display_name="Test User")


class SequenceIds:
    def __init__(self, *values: UUID) -> None:
        self.values = iter(values)

    def __call__(self) -> UUID:
        return next(self.values)


class FakeWorkspaces:
    def __init__(self) -> None:
        self.workspace = WorkspaceModel(
            id=WORKSPACE_ID, name="Trading Workspace V1", created_at=NOW
        )

    async def get(self, workspace_id: UUID) -> WorkspaceModel | None:
        return self.workspace if workspace_id == WORKSPACE_ID else None


class FakeReferenceData:
    def __init__(self) -> None:
        self.venue = TradingVenueModel(
            id=VENUE_ID,
            mic="XETR",
            name="Xetra",
            country_code="DE",
            timezone="Europe/Berlin",
            is_active=True,
            reference_version="FT-001-V1",
            created_at=NOW,
            updated_at=NOW,
        )
        self.currency = CurrencyModel(
            code="EUR",
            name="Euro",
            minor_unit=2,
            is_active=True,
            reference_version="FT-001-V1",
            created_at=NOW,
            updated_at=NOW,
        )

    async def get_trading_venue(self, venue_id: UUID) -> TradingVenueModel | None:
        return self.venue if venue_id == VENUE_ID else None

    async def get_currency(self, code: str) -> CurrencyModel | None:
        return self.currency if code == "EUR" else None


class FakeUnderlyings:
    def __init__(self) -> None:
        self.items: dict[UUID, UnderlyingModel] = {}
        self.flushes = 0

    async def add(self, underlying: UnderlyingModel) -> None:
        self.items[underlying.id] = underlying

    async def get(self, workspace_id: UUID, underlying_id: UUID) -> UnderlyingModel | None:
        item = self.items.get(underlying_id)
        return item if item and item.workspace_id == workspace_id else None

    async def get_with_listings(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> UnderlyingModel | None:
        return await self.get(workspace_id, underlying_id)

    async def find_by_isin(self, workspace_id: UUID, isin: str) -> UnderlyingModel | None:
        return next(
            (x for x in self.items.values() if x.workspace_id == workspace_id and x.isin == isin),
            None,
        )

    async def find_by_wkn(self, workspace_id: UUID, wkn: str) -> UnderlyingModel | None:
        return next(
            (x for x in self.items.values() if x.workspace_id == workspace_id and x.wkn == wkn),
            None,
        )

    async def search(self, *args: Any, **kwargs: Any) -> list[UnderlyingModel]:
        return list(self.items.values())

    async def count_search(self, *args: Any, **kwargs: Any) -> int:
        return len(self.items)

    async def delete(self, underlying: UnderlyingModel) -> None:
        self.items.pop(underlying.id)

    async def flush(self) -> None:
        self.flushes += 1


class FakeListings:
    def __init__(self) -> None:
        self.items: dict[UUID, ListingModel] = {}
        self.flushes = 0

    async def add(self, listing: ListingModel) -> None:
        self.items[listing.id] = listing

    async def get(self, workspace_id: UUID, listing_id: UUID) -> ListingModel | None:
        item = self.items.get(listing_id)
        return item if item and item.workspace_id == workspace_id else None

    async def find_by_venue_ticker(
        self, workspace_id: UUID, venue_id: UUID, ticker: str
    ) -> ListingModel | None:
        return next(
            (
                x
                for x in self.items.values()
                if x.workspace_id == workspace_id
                and x.trading_venue_id == venue_id
                and x.ticker == ticker
            ),
            None,
        )

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> list[ListingModel]:
        return [
            x
            for x in self.items.values()
            if x.workspace_id == workspace_id and x.underlying_id == underlying_id
        ]

    async def flush(self) -> None:
        self.flushes += 1


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[Any] = []
        self.flushes = 0

    async def append(self, event: Any) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        self.flushes += 1


class FakeUsages:
    def __init__(self) -> None:
        self.references: tuple[UsageReference, ...] = ()

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> tuple[UsageReference, ...]:
        return self.references


class FakeUow:
    def __init__(self) -> None:
        self.workspaces = FakeWorkspaces()
        self.reference_data = FakeReferenceData()
        self.underlyings = FakeUnderlyings()
        self.listings = FakeListings()
        self.audit_events = FakeAudit()
        self.usages = FakeUsages()
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type:
            self.rollbacks += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def service(uow: FakeUow, *ids: UUID) -> UnderlyingService:
    return UnderlyingService(uow, clock=lambda: NOW, id_factory=SequenceIds(*ids))


def create_command(isin: str | None = "DE0007236101") -> CreateUnderlying:
    return CreateUnderlying(
        workspace_id=WORKSPACE_ID,
        actor=ACTOR,
        name=" Siemens AG ",
        isin=isin,
        wkn="723610",
        primary_listing=CreateListing(
            trading_venue_id=VENUE_ID,
            ticker=" sie ",
            currency_code="eur",
        ),
    )


@pytest.mark.asyncio
async def test_create_is_atomic_and_writes_two_audit_events() -> None:
    uow = FakeUow()
    result = await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(
        create_command()
    )

    assert result.name == "Siemens AG"
    assert result.quality_status is QualityStatus.COMPLETE
    assert uow.listings.items[LISTING_ID].ticker == "SIE"
    assert len(uow.audit_events.events) == 2
    assert uow.commits == 1
    assert uow.underlyings.flushes == uow.listings.flushes == uow.audit_events.flushes == 1


@pytest.mark.asyncio
async def test_duplicate_isin_aborts_before_commit() -> None:
    uow = FakeUow()
    existing = UnderlyingModel(
        id=UNDERLYING_ID,
        workspace_id=WORKSPACE_ID,
        type="STOCK",
        name="Existing",
        isin="DE0007236101",
        wkn=None,
        lifecycle_status="ACTIVE",
        quality_status="COMPLETE",
        version=1,
        created_at=NOW,
        updated_at=NOW,
        data_origin="MANUAL",
    )
    uow.underlyings.items[existing.id] = existing

    with pytest.raises(DuplicateIsin):
        await service(uow, LISTING_ID, AUDIT_1).create(create_command())

    assert uow.commits == 0
    assert uow.rollbacks == 1
    assert uow.audit_events.events == []


@pytest.mark.asyncio
async def test_noop_update_does_not_commit_or_audit() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.commits = 0
    uow.audit_events.events.clear()

    result = await service(uow).update(
        UpdateUnderlying(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            expected_version=1,
            actor=ACTOR,
            name="Siemens AG",
            isin="DE0007236101",
            wkn="723610",
        )
    )

    assert result.version == 1
    assert uow.commits == 0
    assert uow.audit_events.events == []


@pytest.mark.asyncio
async def test_stale_update_raises_domain_conflict() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())

    with pytest.raises(ConcurrentModification):
        await service(uow).deactivate(
            ChangeUnderlyingStatus(
                workspace_id=WORKSPACE_ID,
                underlying_id=UNDERLYING_ID,
                expected_version=9,
                actor=ACTOR,
            )
        )


@pytest.mark.asyncio
async def test_deactivate_updates_version_and_audits() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.audit_events.events.clear()
    uow.commits = 0

    result = await service(uow, UUID("30000000-0000-4000-8000-000000000003")).deactivate(
        ChangeUnderlyingStatus(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            expected_version=1,
            actor=ACTOR,
        )
    )

    assert result.lifecycle_status is LifecycleStatus.INACTIVE
    assert result.version == 2
    assert uow.audit_events.events[0].change_type.value == "DEACTIVATED"
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_delete_referenced_underlying_is_rejected_with_usage_details() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    reference = UsageReference("WARRANT", UUID("40000000-0000-4000-8000-000000000001"))
    uow.usages.references = (reference,)

    with pytest.raises(UnderlyingDeleteReferenced) as error:
        await service(uow).delete(
            DeleteUnderlying(
                workspace_id=WORKSPACE_ID,
                underlying_id=UNDERLYING_ID,
                expected_version=1,
                actor=ACTOR,
            )
        )

    assert error.value.references == (reference,)
    assert UNDERLYING_ID in uow.underlyings.items


@pytest.mark.asyncio
async def test_add_secondary_listing_commits_and_audits() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.commits = 0
    uow.audit_events.events.clear()
    secondary_id = UUID("20000000-0000-4000-8000-000000000002")
    audit_id = UUID("30000000-0000-4000-8000-000000000004")

    result = await ListingService(
        uow, clock=lambda: NOW, id_factory=SequenceIds(secondary_id, audit_id)
    ).add(
        AddListing(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            actor=ACTOR,
            trading_venue_id=VENUE_ID,
            ticker="SIE2",
            currency_code="EUR",
            is_primary=False,
        )
    )

    assert result.id == secondary_id
    assert result.is_primary is False
    assert len(uow.audit_events.events) == 1
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_search_and_get_return_workspace_scoped_results() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())

    items, total = await service(uow).search(
        SearchUnderlyings(
            workspace_id=WORKSPACE_ID,
            query="Siemens",
            lifecycle_status=LifecycleStatus.ACTIVE,
            offset=0,
            limit=50,
        )
    )
    detail = await service(uow).get(WORKSPACE_ID, UNDERLYING_ID)

    assert total == 1
    assert items[0].id == UNDERLYING_ID
    assert detail.id == UNDERLYING_ID


@pytest.mark.asyncio
async def test_verify_then_master_data_change_resets_quality_status() -> None:
    uow = FakeUow()
    created = await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(
        create_command()
    )
    verified = await service(uow, UUID("30000000-0000-4000-8000-000000000003")).verify(
        ChangeUnderlyingStatus(WORKSPACE_ID, UNDERLYING_ID, created.version, ACTOR)
    )
    verified_status = verified.quality_status

    updated = await service(uow, UUID("30000000-0000-4000-8000-000000000004")).update(
        UpdateUnderlying(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            expected_version=verified.version,
            actor=ACTOR,
            name="Siemens Aktiengesellschaft",
        )
    )

    assert verified_status is QualityStatus.VERIFIED
    assert updated.quality_status is QualityStatus.COMPLETE
    assert updated.version == 3


@pytest.mark.asyncio
async def test_reactivate_inactive_underlying_with_primary_listing() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    deactivated = await service(uow, UUID("30000000-0000-4000-8000-000000000003")).deactivate(
        ChangeUnderlyingStatus(WORKSPACE_ID, UNDERLYING_ID, 1, ACTOR)
    )
    reactivated = await service(uow, UUID("30000000-0000-4000-8000-000000000004")).reactivate(
        ChangeUnderlyingStatus(WORKSPACE_ID, UNDERLYING_ID, deactivated.version, ACTOR)
    )

    assert reactivated.lifecycle_status is LifecycleStatus.ACTIVE
    assert reactivated.version == 3


@pytest.mark.asyncio
async def test_delete_unreferenced_underlying_writes_listing_and_underlying_audits() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.audit_events.events.clear()
    uow.commits = 0

    await service(
        uow,
        UUID("30000000-0000-4000-8000-000000000005"),
        UUID("30000000-0000-4000-8000-000000000006"),
    ).delete(DeleteUnderlying(WORKSPACE_ID, UNDERLYING_ID, 1, ACTOR))

    assert UNDERLYING_ID not in uow.underlyings.items
    assert [event.aggregate_type.value for event in uow.audit_events.events] == [
        "LISTING",
        "UNDERLYING",
    ]
    assert all(event.change_type.value == "DELETED" for event in uow.audit_events.events)
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_listing_update_normalizes_and_audits_actual_change() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.audit_events.events.clear()
    uow.commits = 0

    result = await ListingService(
        uow,
        clock=lambda: NOW,
        id_factory=SequenceIds(UUID("30000000-0000-4000-8000-000000000007")),
    ).update(
        UpdateListing(
            workspace_id=WORKSPACE_ID,
            listing_id=LISTING_ID,
            expected_version=1,
            actor=ACTOR,
            ticker=" sie-new ",
        )
    )

    assert result.ticker == "SIE-NEW"
    assert result.version == 2
    assert uow.audit_events.events[0].field_changes["ticker"] == {
        "old": "SIE",
        "new": "SIE-NEW",
    }
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_listing_noop_update_does_not_commit_or_audit() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    uow.audit_events.events.clear()
    uow.commits = 0

    result = await ListingService(uow, clock=lambda: NOW).update(
        UpdateListing(
            workspace_id=WORKSPACE_ID,
            listing_id=LISTING_ID,
            expected_version=1,
            actor=ACTOR,
            ticker="SIE",
        )
    )

    assert result.version == 1
    assert uow.audit_events.events == []
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_primary_listing_switch_updates_both_listings_atomically() -> None:
    uow = FakeUow()
    await service(uow, UNDERLYING_ID, LISTING_ID, AUDIT_1, AUDIT_2).create(create_command())
    secondary_id = UUID("20000000-0000-4000-8000-000000000002")
    await ListingService(
        uow,
        clock=lambda: NOW,
        id_factory=SequenceIds(
            secondary_id,
            UUID("30000000-0000-4000-8000-000000000003"),
        ),
    ).add(
        AddListing(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            actor=ACTOR,
            trading_venue_id=VENUE_ID,
            ticker="SIE2",
            currency_code="EUR",
            is_primary=False,
        )
    )
    uow.audit_events.events.clear()
    uow.commits = 0

    result = await ListingService(
        uow,
        clock=lambda: NOW,
        id_factory=SequenceIds(
            UUID("30000000-0000-4000-8000-000000000004"),
            UUID("30000000-0000-4000-8000-000000000005"),
        ),
    ).set_primary(
        SetPrimaryListing(
            workspace_id=WORKSPACE_ID,
            underlying_id=UNDERLYING_ID,
            listing_id=secondary_id,
            expected_listing_version=1,
            actor=ACTOR,
        )
    )

    assert result.is_primary is True
    assert uow.listings.items[LISTING_ID].is_primary is False
    assert len(uow.audit_events.events) == 2
    assert all(event.change_type.value == "PRIMARY_CHANGED" for event in uow.audit_events.events)
    assert uow.commits == 1
