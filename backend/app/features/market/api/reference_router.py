"""Controlled reference-data endpoints used by market workflows and FT-002 administration."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.features.market.api.dependencies import (
    get_issuer_administration_service,
    get_reference_data_service,
    get_trading_venue_administration_service,
)
from app.features.market.api.dtos import (
    CreateIssuerRequest,
    CreateTradingVenueRequest,
    CurrencyListResponse,
    CurrencyResponse,
    IssuerAdminListResponse,
    IssuerAdminResponse,
    IssuerListResponse,
    IssuerResponse,
    IssuerVersionRequest,
    TradingVenueAdminListResponse,
    TradingVenueAdminResponse,
    TradingVenueListResponse,
    TradingVenueResponse,
    TradingVenueVersionRequest,
    UpdateIssuerRequest,
    UpdateTradingVenueRequest,
)
from app.features.market.api.errors import translate_market_error
from app.features.market.service.issuer_administration import IssuerAdministrationService
from app.features.market.service.reference_data_service import ReferenceDataService
from app.features.market.service.trading_venue_administration import (
    TradingVenueAdministrationService,
)
from app.features.market.service.types import (
    Actor,
    ChangeIssuerStatus,
    ChangeTradingVenueStatus,
    CreateIssuer,
    CreateTradingVenue,
    UpdateIssuer,
    UpdateTradingVenue,
)

router = APIRouter(prefix="/api/v1/market-reference-data", tags=["market-reference-data"])


def _actor(actor_id: str | None, actor_name: str | None) -> Actor:
    return Actor(id=actor_id, display_name=actor_name or "Trading Workspace User")


@router.get("/issuers", response_model=IssuerListResponse)
async def list_issuers(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> IssuerListResponse:
    """Consumer contract: normal workflows see active issuer reference data only."""
    items = await service.list_active_issuers()
    return IssuerListResponse(items=[IssuerResponse.model_validate(item) for item in items])


@router.get("/issuers/admin", response_model=IssuerAdminListResponse)
async def list_issuers_for_admin(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> IssuerAdminListResponse:
    items = await service.list_issuers()
    return IssuerAdminListResponse(
        items=[IssuerAdminResponse.model_validate(item) for item in items]
    )


@router.get("/issuers/{issuer_id}", response_model=IssuerResponse)
async def get_issuer(
    issuer_id: UUID,
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> IssuerResponse:
    item = await service.get_issuer(issuer_id)
    if item is None or not item.is_active:
        from app.features.market.service.errors import IssuerNotFound

        raise translate_market_error(IssuerNotFound("Issuer does not exist"))
    return IssuerResponse.model_validate(item)


@router.post("/issuers", response_model=IssuerAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_issuer(
    payload: CreateIssuerRequest,
    service: Annotated[IssuerAdministrationService, Depends(get_issuer_administration_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> IssuerAdminResponse:
    try:
        result = await service.create(
            CreateIssuer(
                actor=_actor(x_actor_id, x_actor_name),
                legal_name=payload.legal_name,
                display_name=payload.display_name,
                country_code=payload.country_code,
                lei=payload.lei,
            )
        )
        return IssuerAdminResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


@router.patch("/issuers/{issuer_id}", response_model=IssuerAdminResponse)
async def update_issuer(
    issuer_id: UUID,
    payload: UpdateIssuerRequest,
    service: Annotated[IssuerAdministrationService, Depends(get_issuer_administration_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> IssuerAdminResponse:
    try:
        country_code = payload.country_code if "country_code" in payload.model_fields_set else ...
        lei = payload.lei if "lei" in payload.model_fields_set else ...
        result = await service.update(
            UpdateIssuer(
                issuer_id=issuer_id,
                expected_version=payload.expected_version,
                actor=_actor(x_actor_id, x_actor_name),
                legal_name=payload.legal_name,
                display_name=payload.display_name,
                country_code=country_code,
                lei=lei,
            )
        )
        return IssuerAdminResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


async def _change_issuer_status(
    issuer_id: UUID,
    payload: IssuerVersionRequest,
    service: IssuerAdministrationService,
    actor_id: str | None,
    actor_name: str | None,
    operation: str,
) -> IssuerAdminResponse:
    command = ChangeIssuerStatus(
        issuer_id=issuer_id,
        expected_version=payload.expected_version,
        actor=_actor(actor_id, actor_name),
    )
    result = await getattr(service, operation)(command)
    return IssuerAdminResponse.model_validate(result)


@router.post("/issuers/{issuer_id}/deactivate", response_model=IssuerAdminResponse)
async def deactivate_issuer(
    issuer_id: UUID,
    payload: IssuerVersionRequest,
    service: Annotated[IssuerAdministrationService, Depends(get_issuer_administration_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> IssuerAdminResponse:
    try:
        return await _change_issuer_status(
            issuer_id, payload, service, x_actor_id, x_actor_name, "deactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.post("/issuers/{issuer_id}/reactivate", response_model=IssuerAdminResponse)
async def reactivate_issuer(
    issuer_id: UUID,
    payload: IssuerVersionRequest,
    service: Annotated[IssuerAdministrationService, Depends(get_issuer_administration_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> IssuerAdminResponse:
    try:
        return await _change_issuer_status(
            issuer_id, payload, service, x_actor_id, x_actor_name, "reactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.get("/trading-venues", response_model=TradingVenueListResponse)
async def list_trading_venues(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> TradingVenueListResponse:
    """Consumer contract: normal workflows see active venues only."""
    items = await service.list_active_trading_venues()
    return TradingVenueListResponse(
        items=[TradingVenueResponse.model_validate(item) for item in items]
    )


@router.get("/trading-venues/admin", response_model=TradingVenueAdminListResponse)
async def list_trading_venues_for_admin(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> TradingVenueAdminListResponse:
    """Admin-only read contract including inactive venues and concurrency metadata."""
    items = await service.list_trading_venues()
    return TradingVenueAdminListResponse(
        items=[TradingVenueAdminResponse.model_validate(item) for item in items]
    )


@router.post(
    "/trading-venues",
    response_model=TradingVenueAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trading_venue(
    payload: CreateTradingVenueRequest,
    service: Annotated[
        TradingVenueAdministrationService,
        Depends(get_trading_venue_administration_service),
    ],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> TradingVenueAdminResponse:
    try:
        result = await service.create(
            CreateTradingVenue(
                actor=_actor(x_actor_id, x_actor_name),
                mic=payload.mic,
                name=payload.name,
                country_code=payload.country_code,
                timezone=payload.timezone,
            )
        )
        return TradingVenueAdminResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


@router.patch("/trading-venues/{venue_id}", response_model=TradingVenueAdminResponse)
async def update_trading_venue(
    venue_id: UUID,
    payload: UpdateTradingVenueRequest,
    service: Annotated[
        TradingVenueAdministrationService,
        Depends(get_trading_venue_administration_service),
    ],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> TradingVenueAdminResponse:
    try:
        result = await service.update(
            UpdateTradingVenue(
                venue_id=venue_id,
                expected_version=payload.expected_version,
                actor=_actor(x_actor_id, x_actor_name),
                name=payload.name,
                country_code=payload.country_code,
                timezone=payload.timezone,
            )
        )
        return TradingVenueAdminResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


async def _change_trading_venue_status(
    venue_id: UUID,
    payload: TradingVenueVersionRequest,
    service: TradingVenueAdministrationService,
    actor_id: str | None,
    actor_name: str | None,
    operation: str,
) -> TradingVenueAdminResponse:
    command = ChangeTradingVenueStatus(
        venue_id=venue_id,
        expected_version=payload.expected_version,
        actor=_actor(actor_id, actor_name),
    )
    result = await getattr(service, operation)(command)
    return TradingVenueAdminResponse.model_validate(result)


@router.post(
    "/trading-venues/{venue_id}/deactivate",
    response_model=TradingVenueAdminResponse,
)
async def deactivate_trading_venue(
    venue_id: UUID,
    payload: TradingVenueVersionRequest,
    service: Annotated[
        TradingVenueAdministrationService,
        Depends(get_trading_venue_administration_service),
    ],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> TradingVenueAdminResponse:
    try:
        return await _change_trading_venue_status(
            venue_id, payload, service, x_actor_id, x_actor_name, "deactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.post(
    "/trading-venues/{venue_id}/reactivate",
    response_model=TradingVenueAdminResponse,
)
async def reactivate_trading_venue(
    venue_id: UUID,
    payload: TradingVenueVersionRequest,
    service: Annotated[
        TradingVenueAdministrationService,
        Depends(get_trading_venue_administration_service),
    ],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> TradingVenueAdminResponse:
    try:
        return await _change_trading_venue_status(
            venue_id, payload, service, x_actor_id, x_actor_name, "reactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> CurrencyListResponse:
    items = await service.list_active_currencies()
    return CurrencyListResponse(items=[CurrencyResponse.model_validate(item) for item in items])
