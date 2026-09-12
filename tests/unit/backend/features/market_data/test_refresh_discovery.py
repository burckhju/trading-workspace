from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market_data.service import refresh_discovery as module
from app.features.market_data.service.refresh_discovery import discover_underlying
from app.features.market_data.service.venue_reconciliation import VenueReconciliationStatus


@asynccontextmanager
async def context(session):
    yield session


def setup(monkeypatch):
    workspace, listing_id = uuid4(), uuid4()
    listing = SimpleNamespace(id=listing_id, underlying_id=uuid4(), currency_code="EUR")
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[listing, None]),
        get=AsyncMock(return_value=SimpleNamespace(workspace_id=workspace, isin="US91324P1021")),
    )
    result = SimpleNamespace(
        isin="US91324P1021",
        currency="EUR",
        instrument_type="Common Stock",
        provider_symbol="UNH",
        provider_exchange_code="F",
    )
    adapter = SimpleNamespace(search_instruments=AsyncMock(return_value=[result]))
    container = SimpleNamespace(
        eodhd=SimpleNamespace(adapter=adapter),
        database=SimpleNamespace(session_context=lambda: context(session)),
    )
    reconciliation = SimpleNamespace(
        reconcile=AsyncMock(return_value=SimpleNamespace(status=VenueReconciliationStatus.MATCHED))
    )
    admin = SimpleNamespace(
        create_or_update=AsyncMock(return_value=SimpleNamespace(id=uuid4())),
        validate=AsyncMock(return_value=SimpleNamespace(status=SimpleNamespace(value="ACTIVE"))),
    )
    monkeypatch.setattr(module, "SqlAlchemyMarketDataUnitOfWork", Mock())
    monkeypatch.setattr(module, "MarketDataInstrumentIdentityService", Mock())
    monkeypatch.setattr(
        module, "ProviderVenueReconciliationService", Mock(return_value=reconciliation)
    )
    monkeypatch.setattr(module, "ProviderMappingAdministrationService", Mock(return_value=admin))
    return container, session, adapter, reconciliation, admin, result, workspace, listing_id


@pytest.mark.asyncio
async def test_automatic_stock_mapping_requires_isin_currency_type_and_venue_evidence(monkeypatch):
    container, _session, adapter, _reconciliation, admin, _result, workspace, listing_id = setup(
        monkeypatch
    )
    output = await discover_underlying(container, workspace, listing_id)
    assert output["reason"] == "EODHD_MAPPING_ACTIVE"
    adapter.search_instruments.assert_awaited_once_with("US91324P1021", limit=20)
    command = admin.create_or_update.await_args.args[0]
    assert command.listing_id == listing_id and command.provider_symbol == "UNH"
    assert command.provider_exchange_code == "F"
    admin.validate.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        "isin",
        "currency",
        "type",
        "venue",
        "ambiguous",
        "no_isin",
        "existing",
        "inactive",
        "disabled_provider",
    ],
)
async def test_unverified_stock_identity_or_existing_mapping_never_changes_master_data(
    monkeypatch, failure
):
    container, session, adapter, reconciliation, admin, result, workspace, listing_id = setup(
        monkeypatch
    )
    if failure == "isin":
        result.isin = "DIFFERENT"
    if failure == "currency":
        result.currency = "USD"
    if failure == "type":
        result.instrument_type = "Warrant"
    if failure == "venue":
        reconciliation.reconcile.return_value.status = VenueReconciliationStatus.AMBIGUOUS
    if failure == "ambiguous":
        adapter.search_instruments.return_value += [
            SimpleNamespace(**{**vars(result), "provider_symbol": "OTHER"})
        ]
    if failure == "no_isin":
        session.get.return_value.isin = None
    if failure == "existing":
        session.scalar.side_effect = [
            SimpleNamespace(underlying_id=uuid4()),
            SimpleNamespace(status="DISABLED"),
        ]
    if failure == "inactive":
        session.scalar.side_effect = [None]
    if failure == "disabled_provider":
        container.eodhd = None
    output = await discover_underlying(container, workspace, listing_id)
    assert output["status"] in {"BLOCKED", "AVAILABLE"}
    admin.create_or_update.assert_not_awaited()
    admin.validate.assert_not_awaited()
