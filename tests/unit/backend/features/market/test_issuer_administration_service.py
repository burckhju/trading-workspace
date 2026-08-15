from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest

from app.features.market.persistence.models import IssuerModel
from app.features.market.service.errors import (
    DuplicateIssuerLei,
    IssuerConcurrentModification,
    IssuerNotFound,
)
from app.features.market.service.issuer_administration import IssuerAdministrationService
from app.features.market.service.types import Actor, ChangeIssuerStatus, CreateIssuer, UpdateIssuer

NOW = datetime(2026, 8, 15, 7, 15, tzinfo=UTC)
ISSUER_ID = UUID("10000000-0000-4000-8000-000000000001")
SECOND_ISSUER_ID = UUID("10000000-0000-4000-8000-000000000002")
AUDIT_IDS = (
    UUID("30000000-0000-4000-8000-000000000011"),
    UUID("30000000-0000-4000-8000-000000000012"),
    UUID("30000000-0000-4000-8000-000000000013"),
    UUID("30000000-0000-4000-8000-000000000014"),
)
ACTOR = Actor(id="admin-1", display_name="Reference Admin")
LEI = "529900T8BM49AURSDO55"
SECOND_LEI = "5493001KJTIIGC8Y1R12"


class FakeReferenceData:
    def __init__(self) -> None:
        self.issuers: dict[UUID, IssuerModel] = {}

    async def add_issuer(self, issuer: IssuerModel) -> None:
        self.issuers[issuer.id] = issuer

    async def find_issuer_by_lei(self, lei: str) -> IssuerModel | None:
        canonical = lei.strip().upper()
        return next((issuer for issuer in self.issuers.values() if issuer.lei == canonical), None)

    async def get_issuer(self, issuer_id: UUID) -> IssuerModel | None:
        return self.issuers.get(issuer_id)

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


def service(uow: FakeUow) -> IssuerAdministrationService:
    ids = iter((ISSUER_ID, *AUDIT_IDS, SECOND_ISSUER_ID))
    return IssuerAdministrationService(uow, clock=lambda: NOW, id_factory=lambda: next(ids))


@pytest.mark.asyncio
async def test_create_normalizes_reference_data_and_audits_globally() -> None:
    uow = FakeUow()
    model = await service(uow).create(
        CreateIssuer(
            ACTOR,
            " Société Générale S.A. ",
            " Société Générale ",
            "fr",
            f" {LEI.lower()} ",
        )
    )

    assert model.id == ISSUER_ID
    assert model.legal_name == "Société Générale S.A."
    assert model.display_name == "Société Générale"
    assert model.country_code == "FR"
    assert model.lei == LEI
    assert model.is_active is True
    assert model.version == 1
    assert uow.audit_events.events[0].workspace_id is None
    assert uow.audit_events.events[0].aggregate_type.value == "ISSUER"
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_create_rejects_duplicate_lei_but_not_same_name_without_lei() -> None:
    uow = FakeUow()
    svc = service(uow)
    await svc.create(CreateIssuer(ACTOR, "Issuer AG", "Issuer", "DE", LEI))

    with pytest.raises(DuplicateIssuerLei):
        await svc.create(CreateIssuer(ACTOR, "Other Name", "Other", "DE", LEI.lower()))

    # Name similarity is evidence only; it must not become an automatic identity decision.
    other = await svc.create(CreateIssuer(ACTOR, "Issuer AG", "Issuer", "DE", None))
    assert other.id != ISSUER_ID


@pytest.mark.asyncio
async def test_update_can_clear_optional_fields_and_preserves_identity() -> None:
    uow = FakeUow()
    svc = service(uow)
    model = await svc.create(CreateIssuer(ACTOR, "Issuer AG", "Issuer", "DE", LEI))

    updated = await svc.update(
        UpdateIssuer(
            issuer_id=model.id,
            expected_version=1,
            actor=ACTOR,
            legal_name="Issuer Bank AG",
            country_code=None,
            lei=None,
        )
    )

    assert updated.id == ISSUER_ID
    assert updated.legal_name == "Issuer Bank AG"
    assert updated.country_code is None
    assert updated.lei is None
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_rejects_lei_owned_by_another_issuer() -> None:
    uow = FakeUow()
    svc = service(uow)
    first = await svc.create(CreateIssuer(ACTOR, "First AG", "First", "DE", LEI))
    second = await svc.create(CreateIssuer(ACTOR, "Second AG", "Second", "DE", SECOND_LEI))

    with pytest.raises(DuplicateIssuerLei):
        await svc.update(UpdateIssuer(second.id, 1, ACTOR, lei=first.lei))


@pytest.mark.asyncio
async def test_update_uses_optimistic_concurrency() -> None:
    uow = FakeUow()
    svc = service(uow)
    model = await svc.create(CreateIssuer(ACTOR, "Issuer AG", "Issuer", "DE", LEI))
    updated = await svc.update(UpdateIssuer(model.id, 1, ACTOR, display_name="Issuer Bank"))

    assert updated.display_name == "Issuer Bank"
    assert updated.version == 2
    with pytest.raises(IssuerConcurrentModification):
        await svc.update(UpdateIssuer(model.id, 1, ACTOR, display_name="Old edit"))


@pytest.mark.asyncio
async def test_deactivate_and_reactivate_preserve_identity() -> None:
    uow = FakeUow()
    svc = service(uow)
    model = await svc.create(CreateIssuer(ACTOR, "Issuer AG", "Issuer", "DE", LEI))

    deactivated = await svc.deactivate(ChangeIssuerStatus(model.id, 1, ACTOR))
    assert deactivated.id == ISSUER_ID
    assert deactivated.is_active is False
    assert deactivated.version == 2

    reactivated = await svc.reactivate(ChangeIssuerStatus(model.id, 2, ACTOR))
    assert reactivated.id == ISSUER_ID
    assert reactivated.is_active is True
    assert reactivated.version == 3


@pytest.mark.asyncio
async def test_missing_issuer_is_reported() -> None:
    uow = FakeUow()
    with pytest.raises(IssuerNotFound):
        await service(uow).deactivate(ChangeIssuerStatus(ISSUER_ID, 1, ACTOR))
