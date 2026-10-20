"""The creation contract retains an explicit first listing in the same transaction."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import (
    CurrencyModel,
    IssuerModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.product.api.router import CreateWarrantRequest, router, service
from app.features.product.domain.models import OptionDirection, ProductFamily, WarrantLifecycle
from app.features.product.persistence.models import WarrantModel
from app.features.product.service import application as owner
from app.features.product.service.errors import WarrantServiceError


def payload():
    return {
        "issuer_id": str(uuid4()),
        "underlying_id": str(uuid4()),
        "display_name": "Synthetic combined creation",
        "option_direction": "CALL",
        "strike": "100",
        "strike_currency_code": "USD",
        "maturity_date": "2099-12-31",
        "ratio": "0.1",
        "initial_listing": {
            "trading_venue_id": str(uuid4()),
            "quotation_currency_code": "EUR",
            "symbol": None,
        },
    }


def creation_session():
    session = MagicMock(spec=AsyncSession)

    async def get_reference(model, identity):
        assert model in (CurrencyModel, IssuerModel, TradingVenueModel)
        return SimpleNamespace(is_active=True)

    session.get.side_effect = get_reference
    session.scalar.side_effect = [UnderlyingModel(lifecycle_status=LifecycleStatus.ACTIVE), None]
    return session


def create_args():
    return dict(
        issuer_id=uuid4(),
        underlying_id=uuid4(),
        display_name="Synthetic Call",
        isin=None,
        wkn=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("100"),
        strike_currency_code="USD",
        maturity_date=date(2099, 12, 31),
        ratio=Decimal("0.1"),
    )


def test_create_contract_accepts_complete_listing_and_keeps_currencies_independent():
    parsed = CreateWarrantRequest.model_validate(payload())
    assert parsed.initial_listing.symbol is None
    assert parsed.initial_listing.quotation_currency_code == "EUR"
    assert parsed.strike_currency_code == "USD"


@pytest.mark.parametrize(
    "listing",
    [
        {},
        {"quotation_currency_code": "EUR"},
        {"trading_venue_id": str(uuid4())},
        {"trading_venue_id": str(uuid4()), "quotation_currency_code": "EURO"},
        {"trading_venue_id": str(uuid4()), "quotation_currency_code": "EUR", "guessed": True},
    ],
)
def test_partial_or_unknown_listing_inputs_are_not_silently_dropped(listing):
    with pytest.raises(ValidationError):
        CreateWarrantRequest.model_validate({**payload(), "initial_listing": listing})


def test_legacy_creation_does_not_invent_a_listing():
    old = payload()
    del old["initial_listing"]
    assert CreateWarrantRequest.model_validate(old).initial_listing is None


def test_rest_passes_typed_listing_in_one_creation_command():
    svc = AsyncMock()
    now = datetime.now(UTC)
    svc.create.return_value = WarrantModel(
        id=uuid4(),
        workspace_id=uuid4(),
        issuer_id=uuid4(),
        underlying_id=uuid4(),
        product_family=ProductFamily.WARRANT,
        display_name="Synthetic",
        isin=None,
        wkn=None,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=now,
        updated_at=now,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[service] = lambda: svc
    with TestClient(app) as client:
        result = client.post("/api/v1/warrants", json=payload())
    assert result.status_code == 201, result.text
    svc.create.assert_awaited_once()
    assert isinstance(svc.create.await_args.kwargs["initial_listing"], owner.InitialWarrantListing)
    assert svc.create.await_args.kwargs["initial_listing"].quotation_currency_code == "EUR"
    svc.add_listing.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", [None, "  TEST-CALL  "])
async def test_create_commits_product_terms_and_listing_once(symbol):
    session = creation_session()
    if symbol:
        session.scalar.side_effect = [
            UnderlyingModel(lifecycle_status=LifecycleStatus.ACTIVE),
            None,
            None,
        ]
    workspace, venue = uuid4(), uuid4()
    result = await owner.WarrantService(session).create(
        workspace,
        **create_args(),
        initial_listing=owner.InitialWarrantListing(
            trading_venue_id=venue,
            symbol=symbol,
            quotation_currency_code=" eur ",
        ),
    )
    product, terms, listing = session.add_all.call_args.args[0]
    assert product is result
    assert listing.warrant_id == terms.warrant_id == result.id
    assert listing.workspace_id == result.workspace_id == workspace
    assert listing.trading_venue_id == venue
    assert listing.symbol == ("TEST-CALL" if symbol else None)
    assert listing.quotation_currency_code == "EUR"
    assert terms.strike_currency_code == "USD"
    assert listing.version == product.version == terms.version_no == 1
    session.commit.assert_awaited_once()
    session.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid",
    [
        "missing_venue",
        "inactive_venue",
        "missing_currency",
        "inactive_currency",
        "underlying_symbol",
        "duplicate",
    ],
)
async def test_invalid_listing_does_not_stage_or_commit_any_product(invalid):
    session = creation_session()
    default_get = session.get.side_effect

    async def get_reference(model, identity):
        target = TradingVenueModel if "venue" in invalid else CurrencyModel
        if model is target and (target is TradingVenueModel or identity == "EUR"):
            if invalid.startswith("missing"):
                return None
            if invalid.startswith("inactive"):
                return SimpleNamespace(is_active=False)
        return await default_get(model, identity)

    session.get.side_effect = get_reference
    if invalid == "underlying_symbol":
        session.scalar.side_effect = [
            UnderlyingModel(lifecycle_status=LifecycleStatus.ACTIVE),
            uuid4(),
        ]
    if invalid == "duplicate":
        session.scalar.side_effect = [
            UnderlyingModel(lifecycle_status=LifecycleStatus.ACTIVE),
            None,
            uuid4(),
        ]
    with pytest.raises(WarrantServiceError):
        await owner.WarrantService(session).create(
            uuid4(),
            **create_args(),
            initial_listing=owner.InitialWarrantListing(
                trading_venue_id=uuid4(),
                symbol="TEST",
                quotation_currency_code="EUR",
            ),
        )
    session.add_all.assert_not_called()
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_combined_commit_failure_rolls_back_and_does_not_retry():
    session = creation_session()
    session.commit.side_effect = IntegrityError("INSERT", {}, Exception("constraint"))
    with pytest.raises(WarrantServiceError):
        await owner.WarrantService(session).create(
            uuid4(),
            **create_args(),
            initial_listing=owner.InitialWarrantListing(
                trading_venue_id=uuid4(),
                symbol=None,
                quotation_currency_code="EUR",
            ),
        )
    assert len(session.add_all.call_args.args[0]) == 3
    session.commit.assert_awaited_once()
    session.rollback.assert_awaited_once()
