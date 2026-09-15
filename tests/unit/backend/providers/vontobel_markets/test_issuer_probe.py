from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.market_data.service import refresh as refresh_module
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.providers.vontobel_markets.configure import configure_warrant
from app.providers.vontobel_markets.issuer import supports_issuer_probe
from tests.unit.backend.features.market_data.test_refresh import runtime
from tests.unit.backend.providers.vontobel_markets.test_configure import setup


@pytest.mark.parametrize(
    "name",
    [
        "VONT FINL.",
        "vont finl",
        " VONT.  FINL. ",
        "Vontobel Financial Products GmbH",
        "Bank Vontobel Europe AG",
    ],
)
def test_recognized_names_select_only_a_probe(name):
    assert supports_issuer_probe(name)


@pytest.mark.parametrize(
    "name",
    [
        None,
        "",
        "VONT",
        "VONT FINL something",
        "NotVontobel",
        "Vontobelly",
        "BNP PAR",
        "MS COI.",
        "JP MORGAN",
        "DZ BANK",
        "UBS",
    ],
)
def test_other_or_ambiguous_names_do_not_select_vontobel(name):
    assert not supports_issuer_probe(name)


@pytest.mark.asyncio
async def test_abbreviated_issuer_uses_existing_verified_path():
    session, adapter, workspace, warrant, listing = setup()
    session.get.return_value.legal_name = "VONT FINL."
    await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant)
    adapter.probe.assert_awaited_once()
    assert session.add.call_args.args[0].warrant_listing_id == listing.id
    assert session.get.return_value.legal_name == "VONT FINL."


@pytest.mark.asyncio
async def test_alias_never_bypasses_failed_identity_probe():
    session, adapter, workspace, warrant, _ = setup()
    session.get.return_value.legal_name = "VONT FINL."
    adapter.probe.side_effect = ValueError("IDENTITY_NOT_VERIFIED")
    with pytest.raises(ValueError, match="IDENTITY_NOT_VERIFIED"):
        await configure_warrant(session, adapter, workspace_id=workspace, warrant_id=warrant)
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_uses_same_alias_gate_without_activating_other_sources(monkeypatch):
    value = runtime()
    # Only simulate an already enabled adapter; the test activates no source.
    value.container = replace(value.container, vontobel=object())
    items = [
        RefreshInstrument(uuid4(), name, None, issuer=name, held=True)
        for name in ("VONT FINL.", "JP MORGAN")
    ]
    monkeypatch.setattr(refresh_module, "read_catalog", AsyncMock(return_value=(items, [])))
    value._configure_vontobel = AsyncMock(return_value={"reason": "ISSUER_IDENTITY_VERIFIED"})
    value._warrant = AsyncMock(return_value={"status": "MISSING"})
    await value.run_once()
    value._configure_vontobel.assert_awaited_once_with(items[0])
    assert len(value.jobs) == 3
