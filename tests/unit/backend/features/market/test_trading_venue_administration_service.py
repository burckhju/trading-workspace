from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest

from app.features.market.persistence.models import TradingVenueModel
from app.features.market.service.errors import (
    DuplicateTradingVenueMic,
    TradingVenueConcurrentModification,
)
from app.features.market.service.trading_venue_administration import (
    TradingVenueAdministrationService,
)
from app.features.market.service.types import (
    Actor,
    ChangeTradingVenueStatus,
    CreateTradingVenue,
    UpdateTradingVenue,
)

NOW = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
VENUE_ID = UUID("00000000-0000-4000-8001-000000000001")
AUDIT_ID = UUID("30000000-0000-4000-8000-000000000001")
ACTOR = Actor(id="admin-1", display_name="Reference Admin")


class FakeReferenceData:
    def __init__(self) -> None:
        self.venues: dict[UUID, TradingVenueModel] = {}

    async def add_trading_venue(self, venue: TradingVenueModel) -> None:
        self.venues[venue.id] = venue

    async def find_trading_venue_by_mic(self, mic: str) -> TradingVenueModel | None:
        normalized = mic.strip().upper()
        return next((v for v in self.venues.values() if v.mic == normalized), None)

    async def get_trading_venue(self, venue_id: UUID) -> TradingVenueModel | None:
        return self.venues.get(venue_id)

    async def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def append(self, event: Any) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        return None


class FakeUow:
    def __init__(self) -> None:
        self.reference_data = FakeReferenceData()
        self.audit_events = FakeAudit()
        self.commits = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def service(uow: FakeUow) -> TradingVenueAdministrationService:
    ids = iter(
        (
            VENUE_ID,
            AUDIT_ID,
            UUID("30000000-0000-4000-8000-000000000002"),
            UUID("30000000-0000-4000-8000-000000000003"),
        )
    )
    return TradingVenueAdministrationService(
        uow, clock=lambda: NOW, id_factory=lambda: next(ids)
    )


@pytest.mark.asyncio
async def test_create_normalizes_mic_and_audits_globally() -> None:
    uow = FakeUow()
    model = await service(uow).create(
        CreateTradingVenue(ACTOR, " xetr ", "Xetra", "de", "Europe/Berlin")
    )
    assert (model.mic, model.country_code, model.version, model.reference_version) == (
        "XETR",
        "DE",
        1,
        "FT002_MANUAL_V1",
    )
    assert uow.audit_events.events[0].workspace_id is None
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_create_rejects_case_insensitive_duplicate_mic() -> None:
    uow = FakeUow()
    svc = service(uow)
    await svc.create(CreateTradingVenue(ACTOR, "XETR", "Xetra", "DE", "Europe/Berlin"))
    with pytest.raises(DuplicateTradingVenueMic):
        await svc.create(
            CreateTradingVenue(ACTOR, "xetr", "Duplicate", "DE", "Europe/Berlin")
        )


@pytest.mark.asyncio
async def test_update_uses_expected_version_and_increments_version() -> None:
    uow = FakeUow()
    svc = service(uow)
    model = await svc.create(
        CreateTradingVenue(ACTOR, "XETR", "Xetra", "DE", "Europe/Berlin")
    )
    updated = await svc.update(
        UpdateTradingVenue(model.id, 1, ACTOR, name="Deutsche Börse Xetra")
    )
    assert updated.name == "Deutsche Börse Xetra" and updated.version == 2
    with pytest.raises(TradingVenueConcurrentModification):
        await svc.update(UpdateTradingVenue(model.id, 1, ACTOR, name="Old edit"))


@pytest.mark.asyncio
async def test_deactivate_and_reactivate_preserve_identity() -> None:
    uow = FakeUow()
    svc = service(uow)
    model = await svc.create(
        CreateTradingVenue(ACTOR, "XETR", "Xetra", "DE", "Europe/Berlin")
    )
    deactivated = await svc.deactivate(ChangeTradingVenueStatus(model.id, 1, ACTOR))
    assert (
        deactivated.id == VENUE_ID
        and deactivated.is_active is False
        and deactivated.version == 2
    )
    reactivated = await svc.reactivate(ChangeTradingVenueStatus(model.id, 2, ACTOR))
    assert reactivated.is_active is True and reactivated.version == 3
