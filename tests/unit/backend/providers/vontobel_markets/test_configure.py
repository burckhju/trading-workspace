from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.providers.vontobel_markets.configure import configure_warrant
from tests.unit.backend.providers.vontobel_markets.test_adapter import _adapter, _html, _identity


def setup():
    workspace, warrant_id = uuid4(), uuid4()
    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace,
        lifecycle_status="ACTIVE",
        isin="DE000VH2LU21",
        wkn="VH2LU2",
        issuer_id=uuid4(),
    )
    listing = SimpleNamespace(id=_identity().listing_id, quotation_currency_code="EUR")
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=warrant),
        get=AsyncMock(
            return_value=SimpleNamespace(is_active=True, legal_name="Vontobel Financial Products")
        ),
        scalars=AsyncMock(side_effect=[[listing], []]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
    )
    adapter = SimpleNamespace(
        probe=AsyncMock(
            return_value=(_adapter()._parse(_html(), _identity()), datetime.now(UTC), False)
        )
    )
    return session, adapter, workspace, warrant_id, listing


@pytest.mark.asyncio
async def test_only_verified_issuer_payload_creates_mapping_on_existing_listing():
    session, adapter, workspace, warrant_id, listing = setup()
    assert (
        await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant_id)
        == listing.id
    )
    mapping = session.add.call_args.args[0]
    assert mapping.provider_symbol == "DE000VH2LU21" and mapping.provider_exchange_code == "ISSUER"
    assert mapping.status == "ACTIVE" and mapping.warrant_listing_id == listing.id
    assert mapping.workspace_id == workspace
    session.commit.assert_awaited_once()
    assert session.add.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    ["missing", "inactive", "isin", "issuer", "unlisted", "currency", "quote", "future", "payload"],
)
async def test_unverified_mapping_never_writes(failure):
    session, adapter, workspace, warrant_id, listing = setup()
    if failure == "missing":
        session.scalar.return_value = None
    if failure == "inactive":
        session.scalar.return_value.lifecycle_status = "INACTIVE"
    if failure == "isin":
        session.scalar.return_value.isin = None
    if failure == "issuer":
        session.get.return_value.legal_name = "BNP Paribas"
    if failure == "unlisted":
        session.scalars.side_effect = [[]]
    if failure == "currency":
        session.scalars.side_effect = [[listing, SimpleNamespace(quotation_currency_code="USD")]]
    if failure == "quote":
        adapter.probe.return_value = (None, datetime.now(UTC), False)
    if failure == "future":
        from dataclasses import replace

        quote, retrieved, hit = adapter.probe.return_value
        adapter.probe.return_value = (
            replace(quote, observed_at=datetime.now(UTC) + timedelta(days=1)),
            retrieved,
            hit,
        )
    if failure == "payload":
        adapter.probe.side_effect = ValueError("ISIN mismatch")
    with pytest.raises(ValueError):
        await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant_id)
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [None, "disabled", "workspace", "identity", "exchange", "unvalidated", "duplicate"]
)
async def test_existing_mappings_are_idempotent_and_never_reactivated_or_overwritten(failure):
    session, adapter, workspace, warrant_id, listing = setup()
    mapping = SimpleNamespace(
        workspace_id=workspace,
        warrant_listing_id=listing.id,
        provider_symbol="DE000VH2LU21",
        provider_exchange_code="ISSUER",
        status="ACTIVE",
        validated_at=datetime.now(UTC),
    )
    if failure == "disabled":
        mapping.status = "DISABLED"
    if failure == "workspace":
        mapping.workspace_id = uuid4()
    if failure == "identity":
        mapping.provider_symbol = "UNH"
    if failure == "exchange":
        mapping.provider_exchange_code = "XETR"
    if failure == "unvalidated":
        mapping.validated_at = None
    session.scalars.side_effect = [
        [listing],
        [mapping, mapping] if failure == "duplicate" else [mapping],
    ]
    if failure:
        with pytest.raises(ValueError, match="CONFLICT"):
            await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant_id)
    else:
        assert (
            await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant_id)
            == listing.id
        )
    adapter.probe.assert_not_awaited()
    session.add.assert_not_called()


def test_automatic_issuer_probe_rejects_naive_time_and_does_not_invent_closed_status():
    from app.features.market_data.service.errors import MarketDataInvalidResponseError

    html = _html().replace("2026-09-11T19:59:13+00:00", "2026-09-11T19:59:13")
    with pytest.raises(MarketDataInvalidResponseError, match="timestamp"):
        _adapter()._parse(html, _identity())
    quote = _adapter()._parse(_html().replace('"isOpen": false', '"isOpen": null'), _identity())
    assert quote.trading_status == "UNKNOWN"
