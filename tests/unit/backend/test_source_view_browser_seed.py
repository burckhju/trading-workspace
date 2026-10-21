"""Fail closed before synthetic EOD seed writes; no database/network is used here."""

import asyncio
import importlib
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "00000000-0000-4000-8000-000000000003"
DATABASE = "tw_realized_report_e2e_" + RUN_ID.replace("-", "")
TRADE_ID = UUID("00000000-0000-4000-8000-000000000004")
LISTING_ID = UUID("00000000-0000-4000-8000-000000000005")


@pytest.fixture
def seed_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/e2e/support"))
    return importlib.import_module("seed_source_view_prices")


def test_seed_does_not_open_connection_when_report_guard_rejects(seed_module, monkeypatch):
    guard = AsyncMock(side_effect=RuntimeError("Unmarked or non-disposable database"))
    engine = Mock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr(seed_module, "verify", guard)
    monkeypatch.setattr(seed_module, "create_async_engine", engine)
    with pytest.raises(RuntimeError, match="Unmarked"):
        asyncio.run(seed_module.seed(TRADE_ID, LISTING_ID))
    guard.assert_awaited_once()
    engine.assert_not_called()


def setup_engine(seed_module, monkeypatch, *, database=DATABASE, marker=None, relation=1, count=0):
    connection = Mock()
    connection.scalar = AsyncMock(
        side_effect=[
            database,
            (marker if marker is not None else f"synthetic realized-gross browser {RUN_ID}"),
            relation,
            count,
        ]
    )
    connection.execute = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = connection
    engine = Mock()
    engine.begin.return_value = context
    engine.dispose = AsyncMock()
    monkeypatch.setattr(seed_module, "create_async_engine", Mock(return_value=engine))
    monkeypatch.setattr(
        seed_module,
        "verify",
        AsyncMock(return_value={"database": DATABASE, "run_id": RUN_ID}),
    )
    monkeypatch.setenv("TRADING_WORKSPACE_TEST_DATABASE_URL", "unused-after-mocked-guard")
    return connection, engine


@pytest.mark.parametrize(
    "changed",
    [
        {"database": "production"},
        {"marker": "different-run"},
        {"relation": 0},
        {"count": 1},
    ],
)
def test_seed_rechecks_connection_marker_relation_and_empty_history(
    seed_module, monkeypatch, changed
):
    connection, engine = setup_engine(seed_module, monkeypatch, **changed)
    with pytest.raises(AssertionError):
        asyncio.run(seed_module.seed(TRADE_ID, LISTING_ID))
    connection.execute.assert_not_awaited()
    engine.dispose.assert_awaited_once()


def test_seed_writes_only_twenty_explicit_synthetic_eod_rows(seed_module, monkeypatch):
    connection, engine = setup_engine(seed_module, monkeypatch)
    asyncio.run(seed_module.seed(TRADE_ID, LISTING_ID))
    connection.execute.assert_awaited_once()
    statement, values = connection.execute.call_args.args
    assert str(statement).startswith("INSERT INTO daily_prices ")
    assert "SYNTHETIC-NO-PROVIDER" in str(statement)
    assert len(values) == 20 and len({row["id"] for row in values}) == 20
    assert {row["listing"] for row in values} == {LISTING_ID}
    assert values[0]["day"] == date(2026, 8, 19)
    assert values[-1]["day"] == date(2026, 9, 15)
    assert all(row["day"].weekday() < 5 for row in values)
    assert all(row["day"] < row["now"].date() for row in values)
    engine.dispose.assert_awaited_once()
