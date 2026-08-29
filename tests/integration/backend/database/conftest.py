"""Compatibility fixture for migration qualification tests pinned to the previous head."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings

PREVIOUS_HEAD = "20260827_0028"
CURRENT_HEAD = "20260828_0029"
LEGACY_HEAD_TESTS = {
    "test_daily_price_instrument_migration_postgres.py",
    "test_market_analysis_instrument_migration_postgres.py",
    "test_market_data_instrument_migration_postgres.py",
    "test_provider_mapping_instrument_migration_postgres.py",
}


def _run_alembic(action: str, revision: str, database_url: str) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    config = Config(str(repository_root / "backend" / "alembic.ini"))
    previous = os.environ.get("TRADING_WORKSPACE_DATABASE_URL")
    os.environ["TRADING_WORKSPACE_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        if action == "upgrade":
            command.upgrade(config, revision)
        elif action == "downgrade":
            command.downgrade(config, revision)
        else:
            raise ValueError(action)
    finally:
        if previous is None:
            os.environ.pop("TRADING_WORKSPACE_DATABASE_URL", None)
        else:
            os.environ["TRADING_WORKSPACE_DATABASE_URL"] = previous
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def previous_head_for_legacy_migration_qualifications(request: pytest.FixtureRequest):
    """Run legacy migration qualification cases from their original Alembic head."""

    if request.path.name not in LEGACY_HEAD_TESTS:
        yield
        return

    database_url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not database_url:
        yield
        return

    _run_alembic("downgrade", PREVIOUS_HEAD, database_url)
    try:
        yield
    finally:
        _run_alembic("upgrade", CURRENT_HEAD, database_url)
