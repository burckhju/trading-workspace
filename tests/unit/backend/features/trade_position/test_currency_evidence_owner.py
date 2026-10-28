"""Source ownership, explicit review, correction and read-bound contracts."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.exceptions.types import ApplicationError
from app.features.trade_position.api.currency_evidence import CurrencyEvidenceRequest
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence,
    CurrencyEvidenceLimitExceeded,
    CurrencyListingEvidence,
    evidence_fingerprint,
)
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.service.currency_evidence import (
    CurrencyEvidenceService,
)

AT = datetime(2026, 10, 28, tzinfo=UTC)


def source(**changes):
    return replace(
        CurrencyEvidence(
            id=UUID(int=1),
            workspace_id=UUID(int=2),
            product_id=UUID(int=3),
            kind="HISTORICAL_LISTINGS",
            source_reference="Synthetic exchange archive page 7",
            recorded_at=AT,
            recorded_by=UUID(int=4),
            supersedes_evidence_id=None,
            request_id=UUID(int=5),
            request_fingerprint="a" * 64,
            valid_from=AT - timedelta(days=30),
            valid_to=AT,
            listings=(CurrencyListingEvidence(UUID(int=6), "EUR"),),
            complete_listing_set=True,
        ),
        **changes,
    )


def payload(**changes):
    return {
        "kind": "HISTORICAL_LISTINGS",
        "source_reference": "Synthetic source page 7",
        "confirmation": "CONFIRM_SOURCE_REVIEW",
        "request_id": str(UUID(int=5)),
        "valid_from": "2026-10-01T00:00:00+02:00",
        "valid_to": "2026-10-29T00:00:00+01:00",
        "listings": [{"trading_venue_id": str(UUID(int=6)), "currency_code": "EUR"}],
        "complete_listing_set": True,
        **changes,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"confirmation": None},
        {"confirmation": "USER_CONFIRMED"},
        {"verification": "PROVIDER"},
        {"valid_from": "2026-10-01T00:00:00"},
        {"valid_to": None},
        {"valid_to": "2026-09-01T00:00:00Z"},
        {"listings": []},
        {"complete_listing_set": "true"},
        {"source_reference": "  "},
        {"currency_code": "EUR"},
        {"execution_id": str(UUID(int=20))},
    ],
)
def test_review_and_historical_shape_are_mandatory(change):
    with pytest.raises(ValidationError):
        CurrencyEvidenceRequest(**payload(**change))


def test_duplicate_venues_do_not_manufacture_a_complete_set():
    values = payload()
    values["listings"] *= 2
    with pytest.raises(ValidationError, match="einmal"):
        CurrencyEvidenceRequest(**values)


def test_document_can_supply_exact_venue_without_claiming_its_currency():
    request = CurrencyEvidenceRequest(
        kind="EXECUTION_DOCUMENT",
        source_reference="Synthetic broker receipt",
        request_id=UUID(int=1),
        confirmation="CONFIRM_SOURCE_REVIEW",
        trade_id=UUID(int=2),
        execution_id=UUID(int=3),
        trading_venue_id=UUID(int=4),
    )
    assert request.currency_code is None and request.listings == []
    with pytest.raises(ValidationError, match="Währung oder"):
        CurrencyEvidenceRequest(**{**request.model_dump(), "trading_venue_id": None})


def test_canonical_fingerprint_binds_source_facts_but_not_clock_or_display_order():
    first = source(
        listings=(
            CurrencyListingEvidence(UUID(int=6), "EUR"),
            CurrencyListingEvidence(UUID(int=7), None),
        )
    )
    reordered = replace(
        first,
        id=UUID(int=22),
        recorded_at=AT + timedelta(seconds=2),
        listings=tuple(reversed(first.listings)),
    )
    assert evidence_fingerprint(first) == evidence_fingerprint(reordered)
    for change in [
        {"source_reference": "Corrected source"},
        {"revoked": True},
        {"complete_listing_set": False},
        {"valid_to": AT + timedelta(days=1)},
        {"supersedes_evidence_id": UUID(int=40)},
        {"listings": (CurrencyListingEvidence(UUID(int=6), "USD"),)},
    ]:
        assert evidence_fingerprint(first) != evidence_fingerprint(replace(first, **change))


@pytest.mark.asyncio
async def test_repository_fails_on_overflow_before_parsing_partial_source_set():
    session = Mock(scalars=AsyncMock(return_value=[object(), object()]))
    repository = SqlAlchemyCurrencyEvidenceRepository(session)
    with pytest.raises(CurrencyEvidenceLimitExceeded):
        await repository.list_for_product(UUID(int=2), UUID(int=3), limit=1)
    with pytest.raises(CurrencyEvidenceLimitExceeded):
        await repository.list_for_workspace(UUID(int=2), limit=1)
    with pytest.raises(ValueError, match="positive"):
        await repository.list_for_workspace(UUID(int=2), limit=0)


@pytest.mark.asyncio
async def test_historical_inactive_references_are_allowed_but_unknown_ones_fail():
    session = Mock(scalars=AsyncMock(side_effect=[["EUR"], [UUID(int=6)]]))
    service = CurrencyEvidenceService(session)
    await service._validate_scope(source())
    # No is_active filter can turn historical facts into current validity claims.
    assert "is_active" not in str(session.scalars.await_args_list[0].args[0])
    assert "is_active" not in str(session.scalars.await_args_list[1].args[0])
    session.scalars = AsyncMock(return_value=[])
    with pytest.raises(ApplicationError) as caught:
        await service._validate_scope(source())
    assert caught.value.code == "CURRENCY_NOT_FOUND"
    session.scalars = AsyncMock(side_effect=[["EUR"], []])
    with pytest.raises(ApplicationError) as caught:
        await service._validate_scope(source())
    assert caught.value.code == "TRADING_VENUE_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "trade, execution, code",
    [
        (None, UUID(int=8), "EXECUTION_NOT_FOUND"),
        (SimpleNamespace(cancelled_at=AT), UUID(int=8), "TRADE_CANCELLED"),
        (SimpleNamespace(cancelled_at=None), None, "EXECUTION_NOT_FOUND"),
    ],
)
async def test_document_validates_exact_scope_and_cancelled_trade(trade, execution, code):
    session = Mock(scalar=AsyncMock(side_effect=[trade, execution]))
    service = CurrencyEvidenceService(session)
    evidence = source(
        kind="EXECUTION_DOCUMENT",
        trade_id=UUID(int=7),
        execution_id=UUID(int=8),
        currency_code="EUR",
        valid_from=None,
        valid_to=None,
        listings=(),
        complete_listing_set=False,
    )
    with pytest.raises(ApplicationError) as caught:
        await service._validate_scope(evidence)
    assert caught.value.code == code


@pytest.mark.asyncio
async def test_predecessor_requires_same_scope_and_current_head_but_allows_restoration():
    session = Mock()
    service = CurrencyEvidenceService(session)
    original = source()
    service._repository = SimpleNamespace(
        get=AsyncMock(return_value=original),
        has_successor=AsyncMock(return_value=False),
    )
    corrected = replace(original, id=UUID(int=7), supersedes_evidence_id=original.id)
    await service._validate_predecessor(corrected)
    service._repository.get.return_value = replace(original, revoked=True)
    await service._validate_predecessor(corrected)  # explicit restoration, no lost history
    service._repository.has_successor.return_value = True
    with pytest.raises(ApplicationError) as caught:
        await service._validate_predecessor(corrected)
    assert caught.value.code == "CURRENCY_EVIDENCE_CONFLICT"
    service._repository.has_successor.return_value = False
    service._repository.get.return_value = replace(original, product_id=UUID(int=99))
    with pytest.raises(ApplicationError):
        await service._validate_predecessor(corrected)
    with pytest.raises(ApplicationError):
        await service._validate_predecessor(replace(original, revoked=True))


@pytest.mark.asyncio
async def test_record_is_idempotent_and_never_mutates_source_or_execution():
    session = Mock(add=Mock(), flush=AsyncMock(), commit=AsyncMock(), rollback=AsyncMock())
    service = CurrencyEvidenceService(session)
    service._product = AsyncMock()
    service._validate_scope = AsyncMock()
    service._validate_predecessor = AsyncMock()
    repository = SimpleNamespace(find_request=AsyncMock(return_value=None), add=AsyncMock())
    service._repository = repository
    args = dict(
        workspace_id=UUID(int=2),
        product_id=UUID(int=3),
        actor=UUID(int=4),
        kind="HISTORICAL_LISTINGS",
        source_reference="Verified source",
        request_id=UUID(int=5),
        valid_from=AT - timedelta(days=3),
        valid_to=AT,
        listings=(CurrencyListingEvidence(UUID(int=6), "EUR"),),
        complete_listing_set=True,
        now=AT,
    )
    saved = await service.record(**args)
    assert saved.verification == "USER_VERIFIED_SOURCE"
    assert saved.request_fingerprint == evidence_fingerprint(saved)
    repository.add.assert_awaited_once_with(saved)
    session.commit.assert_awaited_once()
    repository.find_request.return_value = saved
    replay = await service.record(**{**args, "now": AT + timedelta(seconds=3)})
    assert replay == saved
    assert repository.add.await_count == 1 and session.commit.await_count == 1
    with pytest.raises(ApplicationError) as caught:
        await service.record(**{**args, "complete_listing_set": False})
    assert caught.value.code == "CURRENCY_EVIDENCE_REQUEST_CONFLICT"
    assert repository.add.await_count == 1


@pytest.mark.asyncio
async def test_history_limit_is_actionable_and_empty_reads_do_not_write():
    session = Mock(commit=AsyncMock())
    service = CurrencyEvidenceService(session)
    service._product = AsyncMock()
    service._repository = SimpleNamespace(list_for_product=AsyncMock(return_value=()))
    assert await service.history(UUID(int=2), UUID(int=3)) == ()
    session.commit.assert_not_awaited()
    service._repository.list_for_product.side_effect = CurrencyEvidenceLimitExceeded()
    with pytest.raises(ApplicationError) as caught:
        await service.history(UUID(int=2), UUID(int=3))
    assert caught.value.code == "CURRENCY_EVIDENCE_LIMIT"
