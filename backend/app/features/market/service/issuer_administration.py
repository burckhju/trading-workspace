"""Administrative FT-003 use cases for global issuer reference data."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from app.features.market.domain.enums import ActorType, AggregateType, ChangeType, DataOrigin
from app.features.market.persistence.models import AuditEventModel, IssuerModel
from app.features.market.service.errors import (
    DuplicateIssuerLei,
    IssuerConcurrentModification,
    IssuerNotFound,
)
from app.features.market.service.types import ChangeIssuerStatus, CreateIssuer, UpdateIssuer
from app.features.market.service.unit_of_work import MarketUnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class IssuerAdministrationService:
    """Controlled issuer maintenance outside the normal trader workflow."""

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

    async def create(self, command: CreateIssuer) -> IssuerModel:
        legal_name = self._required_name(command.legal_name, "legal_name")
        display_name = self._required_name(command.display_name, "display_name")
        country_code = self._optional_upper(command.country_code)
        lei = self._optional_upper(command.lei)
        async with self._uow:
            await self._ensure_lei_available(lei)
            now = self._clock()
            model = IssuerModel(
                id=self._id_factory(),
                legal_name=legal_name,
                display_name=display_name,
                country_code=country_code,
                lei=lei,
                is_active=True,
                version=1,
                created_at=now,
                updated_at=now,
            )
            await self._uow.reference_data.add_issuer(model)
            await self._audit(
                model, command.actor.id, command.actor.display_name, ChangeType.CREATED, None
            )
            await self._uow.reference_data.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def update(self, command: UpdateIssuer) -> IssuerModel:
        async with self._uow:
            model = await self._require(command.issuer_id)
            self._ensure_version(command.expected_version, model.version)
            before = self._snapshot(model)

            legal_name = (
                self._required_name(command.legal_name, "legal_name")
                if command.legal_name is not None
                else model.legal_name
            )
            display_name = (
                self._required_name(command.display_name, "display_name")
                if command.display_name is not None
                else model.display_name
            )
            country_code = (
                model.country_code
                if command.country_code is ...
                else self._optional_upper(cast(str | None, command.country_code))
            )
            lei = (
                model.lei
                if command.lei is ...
                else self._optional_upper(cast(str | None, command.lei))
            )
            if lei != model.lei:
                await self._ensure_lei_available(lei, excluding=model.id)

            changed = False
            for field, value in (
                ("legal_name", legal_name),
                ("display_name", display_name),
                ("country_code", country_code),
                ("lei", lei),
            ):
                if getattr(model, field) != value:
                    setattr(model, field, value)
                    changed = True
            if not changed:
                return model

            model.version += 1
            model.updated_at = self._clock()
            await self._audit(
                model, command.actor.id, command.actor.display_name, ChangeType.UPDATED, before
            )
            await self._uow.reference_data.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def deactivate(self, command: ChangeIssuerStatus) -> IssuerModel:
        return await self._change_status(command, active=False, change_type=ChangeType.DEACTIVATED)

    async def reactivate(self, command: ChangeIssuerStatus) -> IssuerModel:
        return await self._change_status(command, active=True, change_type=ChangeType.REACTIVATED)

    async def _change_status(
        self, command: ChangeIssuerStatus, *, active: bool, change_type: ChangeType
    ) -> IssuerModel:
        async with self._uow:
            model = await self._require(command.issuer_id)
            self._ensure_version(command.expected_version, model.version)
            if model.is_active is active:
                return model
            before = self._snapshot(model)
            model.is_active = active
            model.version += 1
            model.updated_at = self._clock()
            await self._audit(
                model, command.actor.id, command.actor.display_name, change_type, before
            )
            await self._uow.reference_data.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def _require(self, issuer_id: UUID) -> IssuerModel:
        model = await self._uow.reference_data.get_issuer(issuer_id)
        if model is None:
            raise IssuerNotFound("Issuer does not exist")
        return model

    async def _ensure_lei_available(
        self, lei: str | None, *, excluding: UUID | None = None
    ) -> None:
        if lei is None:
            return
        existing = await self._uow.reference_data.find_issuer_by_lei(lei)
        if existing is not None and existing.id != excluding:
            raise DuplicateIssuerLei("Issuer LEI already exists", field="lei")

    @staticmethod
    def _ensure_version(expected: int, actual: int) -> None:
        if expected != actual:
            raise IssuerConcurrentModification(
                f"Expected version {expected}, found {actual}", field="expected_version"
            )

    @staticmethod
    def _required_name(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            from app.features.market.service.errors import ServiceError

            raise ServiceError(f"{field} must not be blank", field=field)
        return normalized

    @staticmethod
    def _optional_upper(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @staticmethod
    def _snapshot(model: IssuerModel) -> dict[str, Any]:
        return {
            key: getattr(model, key)
            for key in ("legal_name", "display_name", "country_code", "lei", "is_active", "version")
        }

    async def _audit(
        self,
        model: IssuerModel,
        actor_id: str | None,
        actor_name: str,
        change_type: ChangeType,
        before: dict[str, Any] | None,
    ) -> None:
        fields: dict[str, dict[str, Any]] = {}
        for key in ("legal_name", "display_name", "country_code", "lei", "is_active"):
            old = before.get(key) if before else None
            new = getattr(model, key)
            if before is None or old != new:
                fields[key] = {"old": old, "new": new}
        await self._uow.audit_events.append(
            AuditEventModel(
                id=self._id_factory(),
                workspace_id=None,
                aggregate_type=AggregateType.ISSUER,
                aggregate_id=model.id,
                occurred_at=model.updated_at,
                actor_type=ActorType.SYSTEM_USER,
                actor_id=actor_id,
                actor_display_name=actor_name,
                data_origin=DataOrigin.MANUAL,
                change_type=change_type,
                version_before=before.get("version") if before else None,
                version_after=model.version,
                field_changes=fields,
            )
        )
