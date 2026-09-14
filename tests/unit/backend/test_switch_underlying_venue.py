from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.types import ProviderInstrumentSearchItem
from app.providers.eodhd.stock_catalog import (
    StockCatalogDiscovery,
    StockCatalogIdentity,
)
from app.tools import switch_underlying_venue as module

ISIN = "US0378331005"


@asynccontextmanager
async def context(value):
    yield value


def fixture():
    workspace, underlying_id = uuid4(), uuid4()
    source_venue = SimpleNamespace(id=uuid4(), mic="XETR", is_active=True)
    target_venue = SimpleNamespace(id=uuid4(), mic="XFRA")
    source = SimpleNamespace(
        id=uuid4(),
        version=1,
        is_primary=True,
        lifecycle_status="ACTIVE",
        currency_code="EUR",
        trading_venue_id=source_venue.id,
    )
    underlying = SimpleNamespace(
        id=underlying_id,
        name="Example",
        isin=ISIN,
        workspace_id=workspace,
        lifecycle_status="ACTIVE",
    )
    now = datetime.now(UTC)
    proof = StockCatalogIdentity(
        ProviderInstrumentSearchItem(
            MarketDataProvider.EODHD, "APC", "F", isin=ISIN, currency="EUR"
        ),
        "XFRA",
        "/exchange-symbol-list/F",
        now,
        now,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[underlying, target_venue]),
        scalars=AsyncMock(return_value=[source]),
        get=AsyncMock(return_value=source_venue),
    )
    catalog = SimpleNamespace(
        discover_with_search=AsyncMock(return_value=StockCatalogDiscovery("OK", proof))
    )
    container = SimpleNamespace(
        require_eodhd_adapter=Mock(return_value=SimpleNamespace(stock_catalog=catalog)),
        database=SimpleNamespace(session_context=lambda: context(session)),
    )
    return container, session, source, underlying, target_venue, catalog, proof


async def prepare(container, underlying):
    return await module.prepare(
        container,
        workspace_id=underlying.workspace_id,
        isin=ISIN,
        from_mic="XETR",
        to_mic="XFRA",
        currency="EUR",
    )


@pytest.mark.asyncio
async def test_read_only_plan_uses_exact_identity_without_creating_a_listing():
    container, session, source, underlying, venue, catalog, _ = fixture()
    plan = await prepare(container, underlying)
    assert plan.source_id == source.id and plan.target_id is None
    assert plan.target_venue_id == venue.id and plan.summary()["execution_usable"] is False
    catalog.discover_with_search.assert_awaited_once_with(isin=ISIN, currency="EUR", mic="XFRA")
    assert not hasattr(session, "commit")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("missing_underlying", "ACTIVE_UNDERLYING_NOT_FOUND"),
        ("no_primary", "ONE_ACTIVE_PRIMARY_LISTING_REQUIRED"),
        ("wrong_source", "PRIMARY_VENUE_CHANGED"),
        ("currency", "RULE_CURRENCY_CHANGE_NOT_ALLOWED"),
        ("missing_venue", "ACTIVE_TARGET_VENUE_REQUIRED"),
        ("inactive_currency", "ACTIVE_CURRENCY_REQUIRED"),
        ("no_identity", "CATALOG_MISSING"),
        ("wrong_identity", "CATALOG_IDENTITY_MISMATCH"),
        ("conflicting_target", "EXISTING_TARGET_LISTING_CONFLICT"),
        ("ambiguous_target", "TARGET_LISTING_AMBIGUOUS"),
    ],
)
async def test_prepare_rejects_unverified_or_conflicting_changes(mutation, reason):
    container, session, source, underlying, venue, catalog, proof = fixture()
    if mutation == "missing_underlying":
        session.scalar.side_effect = [None]
    if mutation == "no_primary":
        source.is_primary = False
    if mutation == "wrong_source":
        session.get.return_value.mic = "XNAS"
    if mutation == "currency":
        source.currency_code = "USD"
    if mutation == "inactive_currency":
        session.get.return_value.is_active = False
    if mutation == "missing_venue":
        session.scalar.side_effect = [underlying, None]
    if mutation == "no_identity":
        catalog.discover_with_search.return_value = StockCatalogDiscovery("CATALOG_MISSING")
    if mutation == "wrong_identity":
        catalog.discover_with_search.return_value = StockCatalogDiscovery(
            "OK", replace(proof, mic="XNAS")
        )
    if mutation in {"conflicting_target", "ambiguous_target"}:
        target = SimpleNamespace(
            id=uuid4(),
            is_primary=False,
            trading_venue_id=venue.id,
            currency_code="USD",
            ticker="APC",
            lifecycle_status="ACTIVE",
        )
        session.scalars.return_value = [source, target] + (
            [target] if mutation == "ambiguous_target" else []
        )
    with pytest.raises(module.VenueSwitchError, match=reason):
        await prepare(container, underlying)


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["identity", "version", "currency", "primary"])
async def test_primary_switch_checks_snapshot_again(changed):
    container, session, source, underlying, _, _, _ = fixture()
    plan = await prepare(container, underlying)
    session.get.return_value = underlying
    if changed == "identity":
        underlying.isin = "US5949181045"
    if changed == "version":
        source.version = 2
    if changed == "currency":
        source.currency_code = "USD"
    if changed == "primary":
        source.is_primary = False
    with pytest.raises(module.VenueSwitchError, match="CHANGED_DURING_VERIFICATION"):
        await module.check_source(session, plan)


def args(*extra):
    return module.build_parser().parse_args(
        [
            "--workspace-id",
            str(uuid4()),
            "--from-mic",
            "XETR",
            "--to-mic",
            "XFRA",
            "--currency",
            "EUR",
            "--isin",
            ISIN,
            *extra,
        ]
    )


@pytest.mark.asyncio
async def test_batch_deduplicates_isins_defaults_to_dry_run_and_closes(monkeypatch):
    container = SimpleNamespace(
        require_eodhd_adapter=Mock(),
        close=AsyncMock(),
        synchronize_eodhd_account_usage=AsyncMock(),
    )
    monkeypatch.setattr(module.ApplicationContainer, "build", Mock(return_value=container))
    plan = SimpleNamespace(summary=lambda: {"isin": ISIN})
    monkeypatch.setattr(module, "prepare", AsyncMock(return_value=plan))
    monkeypatch.setattr(module, "apply_plan", AsyncMock())
    result = await module.run(args("--isin", ISIN))
    assert result == [{"isin": ISIN, "status": "DRY_RUN", "data_verified": False}]
    module.prepare.assert_awaited_once()
    module.apply_plan.assert_not_awaited()
    container.synchronize_eodhd_account_usage.assert_awaited_once()
    container.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_isolates_errors_redacts_secrets_and_paces(monkeypatch):
    container = SimpleNamespace(
        require_eodhd_adapter=Mock(),
        close=AsyncMock(),
        synchronize_eodhd_account_usage=AsyncMock(),
        settings=SimpleNamespace(
            market_data=SimpleNamespace(refresh=SimpleNamespace(request_spacing_seconds=15))
        ),
    )
    monkeypatch.setattr(module.ApplicationContainer, "build", Mock(return_value=container))
    monkeypatch.setattr(
        module,
        "prepare",
        AsyncMock(side_effect=[RuntimeError("token=secret"), object()]),
    )
    monkeypatch.setattr(module, "apply_plan", AsyncMock(return_value={"status": "APPLIED"}))
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    result = await module.run(args("--isin", "US5949181045", "--apply"))
    assert result[0] == {"isin": ISIN, "status": "BLOCKED", "reason": "RuntimeError"}
    assert result[1]["status"] == "APPLIED"
    module.asyncio.sleep.assert_awaited_once_with(15)
    container.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "extra", [("--isin", "invalid"), ("--to-mic", "XETR"), ("--currency", "US")]
)
async def test_invalid_batch_fails_before_building_container(monkeypatch, extra):
    build = Mock()
    monkeypatch.setattr(module.ApplicationContainer, "build", build)
    with pytest.raises(ValueError):
        await module.run(args(*extra))
    build.assert_not_called()


def test_cli_returns_nonzero_for_partial_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        module,
        "run",
        AsyncMock(return_value=[{"status": "BLOCKED", "reason": "NO_DATA"}]),
    )
    assert (
        module.main(
            [
                "--workspace-id",
                str(uuid4()),
                "--from-mic",
                "XETR",
                "--to-mic",
                "XFRA",
                "--currency",
                "EUR",
                "--isin",
                ISIN,
                "--apply",
            ]
        )
        == 1
    )
    assert "NO_DATA" in capsys.readouterr().out
