from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import CurrencyModel, IssuerModel, UnderlyingModel
from app.features.product.api.router import (
    CreateWarrantRequest,
    TermsRequest,
    TermsResponse,
    router,
    service,
)
from app.features.product.domain.models import OptionDirection, WarrantLifecycle
from app.features.product.persistence.models import WarrantModel, WarrantTermsVersionModel
from app.features.product.service.application import WarrantService
from app.features.product.service.errors import InactiveWarrantReference, WarrantServiceError
from app.features.product_selection.service.repositories import _terms_from_model

NOW = datetime(2026, 9, 12, 8, tzinfo=UTC)
WORKSPACE_ID = uuid4()
WARRANT_ID = uuid4()


def _terms(currency: str | None = None) -> WarrantTermsVersionModel:
    return WarrantTermsVersionModel(
        id=uuid4(),
        warrant_id=WARRANT_ID,
        version_no=1,
        effective_from=NOW,
        effective_to=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("500"),
        strike_currency_code=currency,
        maturity_date=date(2027, 1, 15),
        ratio=Decimal("0.1"),
        created_at=NOW,
    )


def _request() -> dict:
    return {
        "issuer_id": str(uuid4()),
        "underlying_id": str(uuid4()),
        "display_name": "Test Call",
        "option_direction": "CALL",
        "strike": "500",
        "maturity_date": "2027-01-15",
        "ratio": "0.1",
    }


def _terms_request() -> dict:
    return {
        "expected_version": 1,
        "option_direction": "CALL",
        "strike": "500",
        "maturity_date": "2027-01-15",
        "ratio": "0.1",
    }


def test_create_and_terms_contracts_normalize_explicit_currency() -> None:
    created = CreateWarrantRequest.model_validate({**_request(), "strike_currency_code": " usd "})
    changed = TermsRequest.model_validate({**_terms_request(), "strike_currency_code": "usd"})
    assert created.strike_currency_code == "USD"
    assert changed.strike_currency_code == "USD"
    assert created.strike == changed.strike == Decimal("500")


def test_legacy_inputs_remain_unknown_without_eur_default() -> None:
    assert CreateWarrantRequest.model_validate(_request()).strike_currency_code is None
    assert TermsRequest.model_validate(_terms_request()).strike_currency_code is None
    assert TermsResponse.model_validate(_terms()).model_dump()["strike_currency_code"] is None
    assert _terms_from_model(_terms()).strike_currency_code is None


@pytest.mark.parametrize("invalid", ["", "   ", "US", "EURO", "EU1", "€UR", "PT"])
def test_contracts_reject_blank_or_invalid_currency(invalid: str) -> None:
    with pytest.raises(ValidationError):
        CreateWarrantRequest.model_validate({**_request(), "strike_currency_code": invalid})
    with pytest.raises(ValidationError):
        TermsRequest.model_validate({**_terms_request(), "strike_currency_code": invalid})
    with pytest.raises(ValueError, match="strike_currency_code"):
        replace(_terms_from_model(_terms()), strike_currency_code=invalid)


def test_repository_and_response_preserve_currency() -> None:
    model = _terms("USD")
    domain = _terms_from_model(model)
    assert domain.strike_currency_code == "USD"
    assert TermsResponse.model_validate(model).model_dump()["strike_currency_code"] == "USD"
    assert replace(domain, strike_currency_code=" usd ").strike_currency_code == "USD"


def test_strike_comparison_guard_never_compares_usd_with_eur() -> None:
    terms = _terms_from_model(_terms("USD"))
    terms.require_strike_reference_currency(" usd ")
    with pytest.raises(ValueError, match="must match"):
        terms.require_strike_reference_currency("EUR")
    with pytest.raises(ValueError, match="must match"):
        terms.require_strike_reference_currency(None)
    with pytest.raises(ValueError, match="unknown"):
        _terms_from_model(_terms()).require_strike_reference_currency("USD")


def test_nullable_currency_has_reference_constraint_and_no_default() -> None:
    column = WarrantTermsVersionModel.__table__.c.strike_currency_code
    assert column.nullable
    assert column.default is None
    assert column.server_default is None
    assert {fk.target_fullname for fk in column.foreign_keys} == {"currencies.code"}
    assert all(fk.ondelete == "RESTRICT" for fk in column.foreign_keys)


def _creation_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)

    async def get_reference(model, identity):
        if model is CurrencyModel:
            return CurrencyModel(code=identity, is_active=True)
        assert model is IssuerModel
        return IssuerModel(id=identity, is_active=True)

    session.get.side_effect = get_reference
    session.scalar.return_value = UnderlyingModel(lifecycle_status=LifecycleStatus.ACTIVE)
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", [None, " usd "])
async def test_create_persists_strike_currency_without_inference(currency: str | None) -> None:
    session = _creation_session()
    await WarrantService(session).create(
        WORKSPACE_ID,
        issuer_id=uuid4(),
        underlying_id=uuid4(),
        display_name="Test Call",
        isin=None,
        wkn=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("500"),
        strike_currency_code=currency,
        maturity_date=date(2027, 1, 15),
        ratio=Decimal("0.1"),
    )
    warrant, terms = session.add_all.call_args.args[0]
    assert terms.warrant_id == warrant.id
    assert terms.strike_currency_code == ("USD" if currency is not None else None)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["", "US", "EU1", "€UR"])
async def test_service_rejects_invalid_currency_before_lookup(currency: str) -> None:
    session = MagicMock(spec=AsyncSession)
    with pytest.raises(WarrantServiceError) as error:
        await WarrantService(session)._require_strike_currency(currency)
    assert error.value.field == "strike_currency_code"
    session.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [None, False])
async def test_service_rejects_missing_or_inactive_currency(active: bool | None) -> None:
    session = MagicMock(spec=AsyncSession)
    session.get.return_value = (
        None if active is None else CurrencyModel(code="USD", is_active=active)
    )
    expected = WarrantServiceError if active is None else InactiveWarrantReference
    with pytest.raises(expected) as error:
        await WarrantService(session)._require_strike_currency("USD")
    assert error.value.field == "strike_currency_code"
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_currency_correction_creates_new_terms_without_rewriting_history() -> None:
    old = _terms("EUR")
    warrant = WarrantModel(id=WARRANT_ID, version=1, lifecycle_status=WarrantLifecycle.ACTIVE)
    session = MagicMock(spec=AsyncSession)
    session.scalar.side_effect = [warrant, warrant, old, 1]
    session.get.return_value = CurrencyModel(code="USD", is_active=True)

    new = await WarrantService(session).add_terms_version(
        WORKSPACE_ID,
        WARRANT_ID,
        expected_version=1,
        option_direction=OptionDirection.CALL,
        strike=Decimal("500"),
        strike_currency_code="USD",
        maturity_date=date(2027, 1, 15),
        ratio=Decimal("0.1"),
    )
    assert old.strike_currency_code == "EUR"
    assert old.effective_to == new.effective_from
    assert new.strike_currency_code == "USD"
    assert new.version_no == 2
    assert new.id != old.id
    assert warrant.version == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_currency_does_not_close_existing_terms() -> None:
    old = _terms("USD")
    warrant = WarrantModel(id=WARRANT_ID, version=1)
    session = MagicMock(spec=AsyncSession)
    session.scalar.side_effect = [warrant, warrant, old, 1]
    session.get.return_value = None

    with pytest.raises(WarrantServiceError, match="does not exist"):
        await WarrantService(session).add_terms_version(
            WORKSPACE_ID,
            WARRANT_ID,
            expected_version=1,
            option_direction=OptionDirection.CALL,
            strike=Decimal("500"),
            strike_currency_code="ZZZ",
            maturity_date=date(2027, 1, 15),
            ratio=Decimal("0.1"),
        )
    assert old.effective_to is None
    assert old.strike_currency_code == "USD"
    assert warrant.version == 1
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


def test_terms_rest_roundtrip_and_blank_validation() -> None:
    svc = AsyncMock()
    svc.add_terms_version.return_value = _terms("USD")
    svc.terms_history.return_value = [_terms(), _terms("USD")]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[service] = lambda: svc
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/warrants/{WARRANT_ID}/terms",
            json={**_terms_request(), "strike_currency_code": "usd"},
        )
        assert response.status_code == 201
        assert response.json()["strike_currency_code"] == "USD"
        assert svc.add_terms_version.await_args.kwargs["strike_currency_code"] == "USD"
        history = client.get(f"/api/v1/warrants/{WARRANT_ID}/terms")
        assert history.status_code == 200
        assert [row["strike_currency_code"] for row in history.json()] == [None, "USD"]
        invalid = client.post(
            f"/api/v1/warrants/{WARRANT_ID}/terms",
            json={**_terms_request(), "strike_currency_code": " "},
        )
        assert invalid.status_code == 422
        svc.add_terms_version.assert_awaited_once()
