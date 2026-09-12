"""Explicit catalog imports and local currency permissions; never a pricing/FX service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market.domain.enums import (
    ActorType,
    AggregateType,
    ChangeType,
    DataOrigin,
)
from app.features.market.persistence.currency_catalog import (
    CurrencyCatalogReleaseModel,
    CurrencyCatalogStateModel,
)
from app.features.market.persistence.models import AuditEventModel, CurrencyModel
from app.features.market.service.currency_catalog_contract import (
    CurrencyCatalog,
    fingerprint,
)
from app.features.market.service.types import Actor

# Serializes these rare administrative writes across workers, including first activation.
_CATALOG_LOCK = 731924217


def _error(code: str, message: str, status: int = 409) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def _snapshot(row: CurrencyModel | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "code": row.code,
        "name": row.name,
        "minor_unit": row.minor_unit,
        "is_active": row.is_active,
        "reference_version": row.reference_version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def currency_audit_id(code: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trading-workspace/currencies/{code}")


class CurrencyAdministrationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _current(self) -> CurrencyCatalogReleaseModel | None:
        result = await self._session.scalar(
            select(CurrencyCatalogReleaseModel)
            .join(
                CurrencyCatalogStateModel,
                CurrencyCatalogStateModel.release_id == CurrencyCatalogReleaseModel.id,
            )
            .where(CurrencyCatalogStateModel.id == 1)
        )

        return result

    async def list_admin(self) -> dict[str, Any]:
        current = await self._current()
        catalog = CurrencyCatalog.model_validate(current.document) if current else None
        entries = {entry.code: entry for entry in catalog.entries} if catalog else {}
        locals_ = {
            row.code: row
            for row in await self._session.scalars(
                select(CurrencyModel).order_by(CurrencyModel.code)
            )
        }
        items = []
        for code in sorted(entries.keys() | locals_.keys()):
            local, entry = locals_.get(code), entries.get(code)
            active = local.is_active if local else False
            conflict = bool(local and entry and local.minor_unit != entry.minor_unit)
            items.append(
                {
                    "code": code,
                    "name": local.name if local else entries[code].name,
                    "minor_unit": (local.minor_unit if local else entries[code].minor_unit),
                    "catalog_name": entry.name if entry else None,
                    "catalog_minor_unit": entry.minor_unit if entry else None,
                    "numeric_code": entry.numeric_code if entry else None,
                    "local_exists": local is not None,
                    "is_active": active,
                    "catalog_available": entry is not None,
                    "minor_unit_conflict": conflict,
                    "can_activate": entry is not None and not conflict and not active,
                    "reference_version": local.reference_version if local else None,
                    "state_token": self._currency_token(code, local, current),
                }
            )
        return {
            "catalog": current.document if current else None,
            "catalog_checksum": current.checksum if current else None,
            "items": items,
        }

    @staticmethod
    def _currency_token(
        code: str,
        local: CurrencyModel | None,
        current: CurrencyCatalogReleaseModel | None,
    ) -> str:
        return fingerprint(
            {
                "code": code,
                "local": _snapshot(local),
                "catalog": current.checksum if current else None,
            }
        )

    async def preview(self, catalog: CurrencyCatalog) -> dict[str, Any]:
        current = await self._current()
        same_version = await self._session.scalar(
            select(CurrencyCatalogReleaseModel).where(
                CurrencyCatalogReleaseModel.version == catalog.version
            )
        )
        if same_version and same_version.checksum != catalog.checksum:
            raise _error(
                "CURRENCY_CATALOG_VERSION_CONFLICT",
                "Diese Katalogversion existiert bereits mit anderem Inhalt.",
            )
        old = CurrencyCatalog.model_validate(current.document) if current else None
        if old and catalog.source_published_on < old.source_published_on:
            raise _error(
                "CURRENCY_CATALOG_OLDER_SOURCE",
                "Ein älterer Quellenstand darf den aktuellen Katalog nicht ersetzen.",
            )
        before = {entry.code: entry.model_dump() for entry in old.entries} if old else {}
        after = {entry.code: entry.model_dump() for entry in catalog.entries}
        changes = []
        for code in sorted(before.keys() | after.keys()):
            previous, proposed = before.get(code), after.get(code)
            kind = "UNCHANGED"
            if previous is None:
                kind = "NEW"
            elif proposed is None:
                kind = "NOT_IN_NEW_CATALOG"
            elif previous != proposed:
                kind = "CHANGED"
            changes.append({"code": code, "change": kind, "before": previous, "after": proposed})
        return {
            "catalog": catalog.document(),
            "checksum": catalog.checksum,
            "current_version": old.version if old else None,
            "current_checksum": current.checksum if current else None,
            "already_current": bool(current and current.checksum == catalog.checksum),
            "preview_token": fingerprint(
                {
                    "incoming": catalog.checksum,
                    "current": current.checksum if current else None,
                }
            ),
            "changes": changes,
        }

    async def import_catalog(
        self,
        catalog: CurrencyCatalog,
        *,
        expected_preview_token: str,
        reviewed: bool,
        actor: Actor,
    ) -> dict[str, Any]:
        if not reviewed:
            raise _error(
                "CURRENCY_CATALOG_REVIEW_REQUIRED",
                "Quelle und Änderungsvorschau müssen ausdrücklich bestätigt werden.",
                422,
            )
        try:
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _CATALOG_LOCK}
            )
            preview = await self.preview(catalog)
            if preview["already_current"]:
                await self._session.rollback()
                return {
                    "applied": False,
                    "version": catalog.version,
                    "checksum": catalog.checksum,
                }
            if preview["preview_token"] != expected_preview_token:
                raise _error(
                    "CURRENCY_CATALOG_STALE_PREVIEW",
                    "Der Katalog wurde geändert. Bitte eine neue Vorschau erstellen.",
                )
            state = await self._session.get(CurrencyCatalogStateModel, 1)
            if state is None:
                raise _error("CURRENCY_CATALOG_NOT_MIGRATED", "Katalogmigration fehlt.", 503)
            previous_id = state.release_id
            release = await self._session.scalar(
                select(CurrencyCatalogReleaseModel).where(
                    CurrencyCatalogReleaseModel.checksum == catalog.checksum
                )
            )
            if release is None:
                release = CurrencyCatalogReleaseModel(
                    id=uuid4(),
                    version=catalog.version,
                    checksum=catalog.checksum,
                    document=catalog.document(),
                    imported_at=datetime.now(UTC),
                )
                self._session.add(release)
                await self._session.flush()
            state.release_id = release.id
            self._audit(
                release.id,
                AggregateType.CURRENCY_CATALOG,
                ChangeType.UPDATED,
                actor,
                {
                    "catalog_version": {
                        "old": preview["current_version"],
                        "new": catalog.version,
                    },
                    "catalog_checksum": {
                        "old": preview["current_checksum"],
                        "new": catalog.checksum,
                    },
                    "release_id": {
                        "old": str(previous_id) if previous_id else None,
                        "new": str(release.id),
                    },
                },
            )
            await self._session.commit()
            return {
                "applied": True,
                "version": catalog.version,
                "checksum": catalog.checksum,
            }
        except Exception:
            await self._session.rollback()
            raise

    async def change_status(
        self,
        code: str,
        *,
        active: bool,
        expected_token: str,
        actor: Actor,
    ) -> dict[str, Any]:
        try:
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": _CATALOG_LOCK}
            )
            current = await self._current()
            local = await self._session.get(CurrencyModel, code)
            if expected_token != self._currency_token(code, local, current):
                raise _error(
                    "CURRENCY_CONCURRENT_MODIFICATION",
                    "Währung oder Katalog wurde geändert. Bitte neu laden.",
                )
            before = _snapshot(local)
            if active:
                catalog = CurrencyCatalog.model_validate(current.document) if current else None
                entry = (
                    next((e for e in catalog.entries if e.code == code), None) if catalog else None
                )
                if entry is None:
                    raise _error(
                        "CURRENCY_NOT_IN_CATALOG",
                        "Aktivierung nur aus dem aktuell übernommenen Katalog möglich.",
                        422,
                    )
                if local and local.minor_unit != entry.minor_unit:
                    raise _error(
                        "CURRENCY_REFERENCE_CONFLICT",
                        "Untereinheit weicht vom Katalog ab. Keine automatische Korrektur.",
                    )
                assert catalog is not None
                if local is None:
                    now = datetime.now(UTC)
                    local = CurrencyModel(
                        code=code,
                        name=entry.name,
                        minor_unit=entry.minor_unit,
                        is_active=True,
                        reference_version=catalog.version,
                        created_at=now,
                        updated_at=now,
                    )
                    self._session.add(local)
            if local is None:
                raise _error("CURRENCY_NOT_FOUND", "Währung ist lokal nicht vorhanden.", 404)
            if before and local.is_active == active:
                await self._session.rollback()
                return {"code": code, "is_active": active, "changed": False}
            local.is_active = active
            local.updated_at = datetime.now(UTC)
            after = _snapshot(local)
            assert after is not None
            changes = {
                key: {"old": before.get(key) if before else None, "new": value}
                for key, value in after.items()
                if before is None or before.get(key) != value
            }
            changes["catalog_checksum"] = {
                "old": None,
                "new": current.checksum if current else None,
            }
            change = ChangeType.ACTIVATED if active else ChangeType.DEACTIVATED
            self._audit(currency_audit_id(code), AggregateType.CURRENCY, change, actor, changes)
            await self._session.commit()
            return {"code": code, "is_active": active, "changed": True}
        except Exception:
            await self._session.rollback()
            raise

    def _audit(
        self,
        aggregate_id: UUID,
        aggregate_type: AggregateType,
        change: ChangeType,
        actor: Actor,
        changes: dict[str, dict[str, Any]],
    ) -> None:
        self._session.add(
            AuditEventModel(
                id=uuid4(),
                workspace_id=None,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                occurred_at=datetime.now(UTC),
                actor_type=ActorType.SYSTEM_USER,
                actor_id=actor.id,
                actor_display_name=actor.display_name,
                data_origin=DataOrigin.MANUAL,
                change_type=change,
                version_before=None,
                version_after=None,
                field_changes=changes,
            )
        )

    async def history(self) -> list[dict[str, Any]]:
        events = await self._session.scalars(
            select(AuditEventModel)
            .where(
                AuditEventModel.aggregate_type.in_(
                    [AggregateType.CURRENCY, AggregateType.CURRENCY_CATALOG]
                )
            )
            .order_by(AuditEventModel.occurred_at.desc(), AuditEventModel.id.desc())
            .limit(100)
        )
        return [
            {
                "id": str(e.id),
                "occurred_at": e.occurred_at.isoformat(),
                "actor": e.actor_display_name,
                "action": e.change_type.value,
                "aggregate_type": e.aggregate_type.value,
                "changes": e.field_changes,
            }
            for e in events
        ]
