from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.product.domain.models import WarrantLifecycle
from app.features.product.service.application import WarrantService, _up
from app.features.product.service.errors import (
    DuplicateWarrantListing,
    DuplicateWarrantWkn,
    InactiveWarrantReference,
    WarrantConcurrentModification,
    WarrantNotFound,
    WarrantServiceError,
)


@pytest.mark.asyncio
async def test_get_returns_model_and_reports_missing_warrant() -> None:
    workspace_id = uuid4()
    warrant_id = uuid4()
    session = AsyncMock()
    model = SimpleNamespace(id=warrant_id)
    session.scalar.side_effect = [model, None]
    service = WarrantService(session)

    assert await service.get(workspace_id, warrant_id) is model
    with pytest.raises(WarrantNotFound):
        await service.get(workspace_id, warrant_id)


@pytest.mark.asyncio
async def test_list_materializes_scalar_result() -> None:
    session = AsyncMock()
    session.scalars.return_value = [
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(id=uuid4()),
    ]
    service = WarrantService(session)

    assert len(await service.list(uuid4())) == 2


@pytest.mark.asyncio
async def test_change_status_rejects_stale_version_and_is_idempotent() -> None:
    session = AsyncMock()
    service = WarrantService(session)
    model = SimpleNamespace(version=3, lifecycle_status=WarrantLifecycle.ACTIVE)
    service.get = AsyncMock(return_value=model)  # type: ignore[method-assign]

    with pytest.raises(WarrantConcurrentModification):
        await service.change_status(uuid4(), uuid4(), 2, WarrantLifecycle.INACTIVE)

    result = await service.change_status(uuid4(), uuid4(), 3, WarrantLifecycle.ACTIVE)
    assert result is model
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_current_terms_and_history_handle_missing_and_existing_rows() -> None:
    session = AsyncMock()
    service = WarrantService(session)
    service.get = AsyncMock(return_value=SimpleNamespace())  # type: ignore[method-assign]
    session.scalar.side_effect = [None, SimpleNamespace(version_no=2)]

    with pytest.raises(WarrantServiceError, match="no current terms"):
        await service.current_terms(uuid4(), uuid4())
    assert (await service.current_terms(uuid4(), uuid4())).version_no == 2

    session.scalars.return_value = [
        SimpleNamespace(version_no=1),
        SimpleNamespace(version_no=2),
    ]
    history = await service.terms_history(uuid4(), uuid4())
    assert [item.version_no for item in history] == [1, 2]


@pytest.mark.asyncio
async def test_add_listing_validates_references_and_normalizes_values() -> None:
    session = AsyncMock()
    session.add = Mock()
    service = WarrantService(session)
    service.get = AsyncMock(return_value=SimpleNamespace())  # type: ignore[method-assign]
    session.get.side_effect = [
        SimpleNamespace(is_active=True),
        SimpleNamespace(is_active=True),
    ]
    session.scalar.return_value = None

    listing = await service.add_listing(
        uuid4(),
        uuid4(),
        trading_venue_id=uuid4(),
        symbol="  abc123 ",
        quotation_currency_code=" eur ",
    )

    assert listing.symbol == "ABC123"
    assert listing.quotation_currency_code == "EUR"
    assert listing.lifecycle_status is WarrantLifecycle.ACTIVE
    session.add.assert_called_once_with(listing)
    session.commit.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_add_listing_rejects_blank_symbol_inactive_venue_and_duplicate() -> None:
    session = AsyncMock()
    service = WarrantService(session)
    service.get = AsyncMock(return_value=SimpleNamespace())  # type: ignore[method-assign]

    with pytest.raises(WarrantServiceError, match="symbol must not be blank"):
        await service.add_listing(
            uuid4(),
            uuid4(),
            trading_venue_id=uuid4(),
            symbol="  ",
            quotation_currency_code="EUR",
        )

    session.get.return_value = SimpleNamespace(is_active=False)
    with pytest.raises(InactiveWarrantReference, match="Trading venue is inactive"):
        await service.add_listing(
            uuid4(),
            uuid4(),
            trading_venue_id=uuid4(),
            symbol="ABC",
            quotation_currency_code="EUR",
        )

    session.get.side_effect = [
        SimpleNamespace(is_active=True),
        SimpleNamespace(is_active=True),
    ]
    session.scalar.return_value = uuid4()
    with pytest.raises(DuplicateWarrantListing):
        await service.add_listing(
            uuid4(),
            uuid4(),
            trading_venue_id=uuid4(),
            symbol="ABC",
            quotation_currency_code="EUR",
        )


@pytest.mark.asyncio
async def test_commit_translates_remaining_constraints_and_unknown_integrity_error() -> None:
    cases = [
        ("uq_warrants_workspace_wkn", DuplicateWarrantWkn),
        ("uq_warrant_listings_workspace_venue_symbol", DuplicateWarrantListing),
        ("uq_warrant_terms_versions_open", WarrantConcurrentModification),
        ("some_other_constraint", WarrantServiceError),
    ]
    for constraint, expected in cases:
        session = AsyncMock()
        session.commit.side_effect = IntegrityError(
            "insert", {}, Exception(f"duplicate key violates constraint {constraint}")
        )
        service = WarrantService(session)
        with pytest.raises(expected):
            await service._commit()
        session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_commit_rolls_back_and_reraises_unexpected_error() -> None:
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("boom")
    service = WarrantService(session)

    with pytest.raises(RuntimeError, match="boom"):
        await service._commit()
    session.rollback.assert_awaited_once_with()


def test_term_validation_and_identifier_normalization() -> None:
    WarrantService._validate_terms(Decimal("0"), Decimal("0.1"))
    with pytest.raises(WarrantServiceError, match="non-negative"):
        WarrantService._validate_terms(Decimal("-1"), Decimal("0.1"))
    with pytest.raises(WarrantServiceError, match="greater than zero"):
        WarrantService._validate_terms(Decimal("1"), Decimal("0"))

    assert _up(None) is None
    assert _up("  de000abc1234 ") == "DE000ABC1234"
    assert _up("   ") is None
