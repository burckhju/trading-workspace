"""Administrative FT-002 use cases for global trading-venue reference data."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.features.market.domain.enums import ActorType, AggregateType, ChangeType, DataOrigin
from app.features.market.persistence.models import AuditEventModel, TradingVenueModel
from app.features.market.service.errors import (
    DuplicateTradingVenueMic,
    TradingVenueConcurrentModification,
    TradingVenueNotFound,
)
from app.features.market.service.types import (
    ChangeTradingVenueStatus,
    CreateTradingVenue,
    UpdateTradingVenue,
)
from app.features.market.service.unit_of_work import MarketUnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


class TradingVenueAdministrationService:
    """Rare admin/system maintenance; not part of the normal trader workflow."""

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

    async def create(self, command: CreateTradingVenue) -> TradingVenueModel:
        mic = command.mic.strip().upper()
        async with self._uow:
            if await self._uow.reference_data.find_trading_venue_by_mic(mic):
                raise DuplicateTradingVenueMic("Trading venue MIC already exists", field="mic")
            now = self._clock()
            model = TradingVenueModel(
                id=self._id_factory(),
                mic=mic,
                name=command.name.strip(),
                country_code=command.country_code.strip().upper(),
                timezone=command.timezone.strip(),
                is_active=True,
                reference_version="FT002_MANUAL_V1",
                version=1,
                created_at=now,
                updated_at=now,
            )
            await self._uow.reference_data.add_trading_venue(model)
            await self._audit(
                model, command.actor.id, command.actor.display_name, ChangeType.CREATED, None
            )
            await self._uow.reference_data.flush()
            await self._uow.audit_events.flush()
            await self._uow.commit()
            return model

    async def update(self, command: UpdateTradingVenue) -> TradingVenueModel:
        async with self._uow:
            model = await self._require(command.venue_id)
            self._ensure_version(command.expected_version, model.version)
            before = self._snapshot(model)
            changed = False
            for field, value in (
                ("name", command.name),
                ("country_code", command.country_code),
                ("timezone", command.timezone),
            ):
                if value is None:
                    continue
                normalized = value.strip().upper() if field == "country_code" else value.strip()
                if getattr(model, field) != normalized:
                    setattr(model, field, normalized)
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

    async def deactivate(self, command: ChangeTradingVenueStatus) -> TradingVenueModel:
        return await self._change_status(command, active=False, change_type=ChangeType.DEACTIVATED)

    async def reactivate(self, command: ChangeTradingVenueStatus) -> TradingVenueModel:
        return await self._change_status(command, active=True, change_type=ChangeType.REACTIVATED)

    async def _change_status(
        self, command: ChangeTradingVenueStatus, *, active: bool, change_type: ChangeType
    ) -> TradingVenueModel:
        async with self._uow:
            model = await self._require(command.venue_id)
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

    async def _require(self, venue_id: UUID) -> TradingVenueModel:
        model = await self._uow.reference_data.get_trading_venue(venue_id)
        if model is None:
            raise TradingVenueNotFound("Trading venue does not exist")
        return model

    @staticmethod
    def _ensure_version(expected: int, actual: int) -> None:
        if expected != actual:
            raise TradingVenueConcurrentModification(
                f"Expected version {expected}, found {actual}", field="expected_version"
            )

    @staticmethod
    def _snapshot(model: TradingVenueModel) -> dict[str, Any]:
        return {
            k: getattr(model, k)
            for k in ("name", "country_code", "timezone", "is_active", "version")
        }

    async def _audit(
        self,
        model: TradingVenueModel,
        actor_id: str | None,
        actor_name: str,
        change_type: ChangeType,
        before: dict[str, Any] | None,
    ) -> None:
        fields: dict[str, dict[str, Any]] = {}
        for key in ("mic", "name", "country_code", "timezone", "is_active"):
            old = before.get(key) if before else None
            new = getattr(model, key)
            if before is None or old != new:
                fields[key] = {"old": old, "new": new}
        await self._uow.audit_events.append(
            AuditEventModel(
                id=self._id_factory(),
                workspace_id=None,
                aggregate_type=AggregateType.TRADING_VENUE,
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
