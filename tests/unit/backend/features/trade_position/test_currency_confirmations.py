"""Explicit provenance, stable legacy retries and caller-owned transactions."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.exceptions.types import ApplicationError
from app.features.learning.api.dtos import ExecuteAsTradeRequest
from app.features.learning.application.execute_as_trade_service import (
    request_fingerprint,
)
from app.features.trade_position.api.dtos import (
    ExecutionCorrectionRequest,
    ExecutionCurrencyConfirmationRequest,
    ExecutionCurrencyDeclarationRequest,
    ExternalPurchaseRequest,
)
from app.features.trade_position.api.router import _capture_time
from app.features.trade_position.domain.currency import (
    ExecutionCurrencyDeclaration,
    ExecutionCurrencySource,
)
from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.currency_confirmations import (
    ExecutionCurrencyConfirmationService,
    confirmation_fingerprint,
)

AT = datetime(2026, 8, 17, 8, tzinfo=UTC)
DECLARATION = ExecutionCurrencyDeclaration("EUR", ExecutionCurrencySource.USER_CONFIRMED)


def execution() -> ExecutionRecord:
    return ExecutionRecord(
        id=UUID(int=4),
        trade_id=UUID(int=3),
        product_id=UUID(int=5),
        quantity=10,
        price_per_unit=Decimal("2.50"),
        executed_at=AT,
        recorded_at=AT,
        recorded_by=UUID(int=6),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"currency_code": "EUR"},
        {"currency_code": "EUR", "source": "LISTING"},
        {"currency_code": "EU", "source": "USER_CONFIRMED"},
        {"currency_code": "€UR", "source": "USER_CONFIRMED"},
        {"currency_code": "EUR", "source": "USER_CONFIRMED", "note": "  "},
    ],
)
def test_declaration_requires_explicit_valid_source(payload):
    with pytest.raises(ValidationError):
        ExecutionCurrencyDeclarationRequest(**payload)


def test_unknown_capture_and_correction_never_acquire_a_currency_default():
    body = dict(quantity=10, price_per_unit="2.50", executed_at=AT)
    purchase = ExternalPurchaseRequest(product_id=UUID(int=5), **body)
    correction = ExecutionCorrectionRequest(side="BUY", **body)
    learning = ExecuteAsTradeRequest(**body)
    assert purchase.currency_confirmation is None
    assert correction.currency_confirmation is None
    assert learning.currency_confirmation is None
    assert "currency_confirmation" not in _capture_time(purchase)
    assert "currency_confirmation" not in _capture_time(correction)
    assert (
        ExecutionCurrencyDeclarationRequest(
            currency_code=" eur ", source="USER_CONFIRMED"
        ).to_domain()
        == DECLARATION
    )


def test_legacy_and_new_capture_request_identity_are_distinct_and_stable():
    args = (UUID(int=1), UUID(int=2), "sale:example", 10, Decimal("2.50"), AT)
    old = TradePositionService._request_identity(*args)
    assert old == (
        "4899549e45f8be781dea1e36467a6e8b446c0429cc541ec1771cfd9cea07686d",
        "bece627be4673e758fc90df4c095f9cb2212443cde42523ab52a6a7e054a7ae7",
    )
    confirmed = TradePositionService._request_identity(*args, currency_confirmation=DECLARATION)
    changed = TradePositionService._request_identity(
        *args, currency_confirmation=replace(DECLARATION, currency_code="USD")
    )
    assert old[0] == confirmed[0] == changed[0]
    assert len({old[1], confirmed[1], changed[1]}) == 3
    assert confirmed == TradePositionService._request_identity(
        *args, currency_confirmation=DECLARATION
    )
    assert old == TradePositionService._request_identity(*args, currency_confirmation=None)


def test_learning_retry_binds_confirmation_without_changing_old_payloads():
    args = dict(
        observation_id=UUID(int=3),
        quantity=10,
        price_per_unit=Decimal("2.50"),
        executed_at=AT,
    )
    old = request_fingerprint(**args)
    assert old == "7e1bb84726072dfb94234893d4b3f33b04165a1d30c570611706501153bed417"
    assert old == request_fingerprint(**args, currency_confirmation=None)
    assert old != request_fingerprint(**args, currency_confirmation=DECLARATION)
    assert request_fingerprint(**args, currency_confirmation=DECLARATION) != request_fingerprint(
        **args, currency_confirmation=replace(DECLARATION, note="Exact broker statement")
    )


def test_explicit_confirmation_retry_binds_exact_execution_and_predecessor():
    values = dict(
        trade_id=UUID(int=3),
        execution_id=UUID(int=4),
        declaration=DECLARATION,
        supersedes_confirmation_id=None,
    )
    original = confirmation_fingerprint(**values)
    assert original != confirmation_fingerprint(**{**values, "execution_id": UUID(int=7)})
    assert original != confirmation_fingerprint(
        **{**values, "supersedes_confirmation_id": UUID(int=8)}
    )
    with pytest.raises(ValidationError):
        ExecutionCurrencyConfirmationRequest(currency_code="EUR", source="USER_CONFIRMED")


@pytest.mark.asyncio
async def test_capture_preserves_execution_and_keeps_commit_with_the_caller():
    session = Mock(flush=AsyncMock(), commit=AsyncMock())
    owner = ExecutionCurrencyConfirmationService(session)
    owner._currencies = SimpleNamespace(
        get_currency=AsyncMock(return_value=SimpleNamespace(is_active=False))
    )
    owner._repository = SimpleNamespace(add=AsyncMock())
    original = execution()
    enriched = await owner.capture(
        workspace_id=UUID(int=1),
        execution=original,
        declaration=DECLARATION,
        actor=UUID(int=6),
    )
    fact = enriched.currency_confirmation
    assert fact is not None
    assert fact.execution_id == original.id and fact.trade_id == original.trade_id
    assert fact.currency_code == "EUR" and fact.confirmed_at != original.executed_at
    assert replace(enriched, currency_confirmation=None) == original
    assert original.currency_confirmation is None
    owner._repository.add.assert_awaited_once_with(fact)
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
    with pytest.raises(FrozenInstanceError):
        fact.currency_code = "USD"
    with pytest.raises(ValueError, match="does not belong"):
        replace(original, currency_confirmation=replace(fact, execution_id=UUID(int=99)))


@pytest.mark.asyncio
async def test_unknown_currency_fails_before_capture_provenance_is_inserted():
    session = Mock(flush=AsyncMock(), commit=AsyncMock())
    owner = ExecutionCurrencyConfirmationService(session)
    owner._currencies = SimpleNamespace(get_currency=AsyncMock(return_value=None))
    owner._repository = SimpleNamespace(add=AsyncMock())
    with pytest.raises(ApplicationError) as error:
        await owner.capture(
            workspace_id=UUID(int=1),
            execution=execution(),
            declaration=replace(DECLARATION, currency_code="ZZZ"),
            actor=UUID(int=6),
        )
    assert error.value.code == "CURRENCY_NOT_FOUND"
    session.flush.assert_not_awaited()
    owner._repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_history_derives_current_from_its_single_returned_source_set():
    session = Mock(scalar=AsyncMock(return_value=UUID(int=4)), commit=AsyncMock())
    owner = ExecutionCurrencyConfirmationService(session)
    first = owner._new_confirmation(
        workspace_id=UUID(int=1),
        trade_id=UUID(int=3),
        execution_id=UUID(int=4),
        declaration=DECLARATION,
        actor=UUID(int=6),
        request_id=UUID(int=7),
        supersedes_confirmation_id=None,
    )
    second = replace(
        first, id=UUID(int=8), currency_code="USD", supersedes_confirmation_id=first.id
    )
    owner._repository = SimpleNamespace(history=AsyncMock(return_value=(second, first)))
    current, history = await owner.history(UUID(int=1), UUID(int=3), UUID(int=4))
    assert current == second and history == (second, first)
    owner._repository.history.assert_awaited_once()
    session.commit.assert_not_awaited()
