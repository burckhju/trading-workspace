"""Catalog-backed currency administration, distinct from active consumer references."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.database.dependencies import get_database_session
from app.features.market.service.currency_administration import (
    CurrencyAdministrationService,
)
from app.features.market.service.currency_catalog_contract import (
    Code,
    CurrencyCatalog,
    Digest,
    bundled_catalog,
    parse_catalog,
)
from app.features.market.service.types import Actor

router = APIRouter(prefix="/currencies", tags=["currency-administration"])


class CatalogPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_json: str | None = Field(default=None, max_length=256_000)


class CatalogImportRequest(CatalogPreviewRequest):
    expected_preview_token: Digest
    reviewed: Literal[True]


class CurrencyStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_token: Digest


def _catalog(payload: CatalogPreviewRequest) -> CurrencyCatalog:
    try:
        return (
            bundled_catalog()
            if payload.catalog_json is None
            else parse_catalog(payload.catalog_json)
        )
    except (ValueError, RecursionError) as exc:
        raise ApplicationError(
            code="CURRENCY_CATALOG_INVALID",
            status_code=422,
            message="Ungültiger Katalog: Format, Codes, Untereinheiten und Quellenstand prüfen.",
        ) from exc


def _actor(
    x_actor_id: Annotated[str | None, Header(max_length=100)] = None,
    x_actor_name: Annotated[str | None, Header(max_length=200)] = None,
) -> Actor:
    # Same trusted local-deployment identity convention as issuer/venue administration.
    # These audit headers are not authentication or authorization.
    return Actor(
        id=x_actor_id,
        display_name=(x_actor_name or "Trading Workspace User").strip() or "Trading Workspace User",
    )


Session = Annotated[AsyncSession, Depends(get_database_session)]
AuditActor = Annotated[Actor, Depends(_actor)]


@router.get("/admin")
async def list_currencies_for_admin(session: Session) -> dict[str, Any]:
    return await CurrencyAdministrationService(session).list_admin()


@router.get("/admin/history")
async def currency_history(session: Session) -> dict[str, Any]:
    return {"items": await CurrencyAdministrationService(session).history()}


@router.post("/catalog/preview")
async def preview_catalog(payload: CatalogPreviewRequest, session: Session) -> dict[str, Any]:
    return await CurrencyAdministrationService(session).preview(_catalog(payload))


@router.post("/catalog/import")
async def import_catalog(
    payload: CatalogImportRequest,
    session: Session,
    actor: AuditActor,
) -> dict[str, Any]:
    return await CurrencyAdministrationService(session).import_catalog(
        _catalog(payload),
        expected_preview_token=payload.expected_preview_token,
        reviewed=payload.reviewed,
        actor=actor,
    )


@router.post("/{code}/activate")
async def activate_currency(
    code: Code,
    payload: CurrencyStatusRequest,
    session: Session,
    actor: AuditActor,
) -> dict[str, Any]:
    return await CurrencyAdministrationService(session).change_status(
        code,
        active=True,
        expected_token=payload.expected_token,
        actor=actor,
    )


@router.post("/{code}/deactivate")
async def deactivate_currency(
    code: Code,
    payload: CurrencyStatusRequest,
    session: Session,
    actor: AuditActor,
) -> dict[str, Any]:
    return await CurrencyAdministrationService(session).change_status(
        code,
        active=False,
        expected_token=payload.expected_token,
        actor=actor,
    )
