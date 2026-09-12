from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.providers.frankfurt_quotes import configure
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
from tests.unit.backend.providers.frankfurt_quotes.test_public import (
    public_settings,
    wire,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW


def context():
    workspace, warrant_id = uuid4(), uuid4()
    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace,
        lifecycle_status="ACTIVE",
        isin="DE000VH2LU21",
    )
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[warrant, SimpleNamespace(is_active=True), None]),
        scalars=AsyncMock(side_effect=[[], []]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
    )
    client = SimpleNamespace(
        settings=public_settings(),
        load_public=AsyncMock(
            return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
        ),
    )
    return session, client, workspace, warrant_id, warrant


@pytest.mark.asyncio
@pytest.mark.parametrize("apply", [False, True])
async def test_dry_run_and_explicit_apply_use_verified_identity_without_historical_mutations(
    apply,
):
    session, client, workspace, warrant_id, _ = context()
    result = await configure.configure_warrant(
        session, client, workspace_id=workspace, warrant_id=warrant_id, apply=apply
    )
    assert result["status"] == ("APPLIED" if apply else "DRY_RUN")
    assert result["create_listing"] is result["create_venue"] is result["create_mapping"] is True
    assert result["provider_identity"] == "DE000VH2LU21"
    assert result["provider_exchange_code"] == "XSC"
    assert result["venue_mic"] == "XFRA"
    assert result["analysis_usable"] is True
    assert result["execution_usable"] is False
    client.load_public.assert_awaited_once_with("DE000VH2LU21")
    sql = str(session.scalar.call_args_list[0].args[0])
    assert "warrants.workspace_id" in sql
    if apply:
        session.commit.assert_awaited_once()
        assert session.add.call_count == 3
        venue, listing, mapping = [call.args[0] for call in session.add.call_args_list]
        assert venue.mic == "XFRA"
        assert listing.symbol is None
        assert listing.quotation_currency_code == "EUR"
        assert mapping.warrant_listing_id == listing.id
        assert mapping.validated_at == NOW
    else:
        session.add.assert_not_called()
        session.flush.assert_not_awaited()
        session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_workspace_warrant_is_rejected_before_network():
    session, client, workspace, warrant_id, _ = context()
    session.scalar.side_effect = [None]
    with pytest.raises(ValueError, match="requested workspace"):
        await configure.configure_warrant(
            session, client, workspace_id=workspace, warrant_id=warrant_id
        )
    client.load_public.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["mode", "identity", "currency", "venue", "listing", "mapping"])
async def test_setup_conflicts_do_not_change_existing_data(failure):
    session, client, workspace, warrant_id, warrant = context()
    if failure == "mode":
        client.settings = public_settings(source_mode="https_json")
    elif failure == "identity":
        client.load_public.return_value = (
            FrankfurtPublicPrice.model_validate(wire(isin="US91324P1021")),
            NOW,
            False,
        )
    elif failure == "currency":
        session.scalar.side_effect = [warrant, None]
    elif failure == "venue":
        session.scalar.side_effect = [
            warrant,
            SimpleNamespace(is_active=True),
            SimpleNamespace(is_active=False),
        ]
    elif failure == "listing":
        session.scalars.side_effect = [[SimpleNamespace(lifecycle_status="INACTIVE")]]
    else:
        session.scalars.side_effect = [[], [SimpleNamespace(workspace_id=uuid4())]]
    with pytest.raises(ValueError):
        await configure.configure_warrant(
            session, client, workspace_id=workspace, warrant_id=warrant_id, apply=True
        )
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


def test_cli_reports_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(
        configure, "run", AsyncMock(side_effect=ValueError("configuration rejected"))
    )
    with pytest.raises(SystemExit) as exc:
        configure.main(["--warrant-id", str(uuid4())])
    assert exc.value.code == 1
    assert "configuration rejected" in capsys.readouterr().err


def test_cli_success_is_machine_readable(monkeypatch, capsys):
    monkeypatch.setattr(configure, "run", AsyncMock(return_value={"status": "DRY_RUN"}))
    assert configure.main(["--warrant-id", str(uuid4())]) == 0
    assert '"status": "DRY_RUN"' in capsys.readouterr().out
