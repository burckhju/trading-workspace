"""Tests for the initial FT-001 Alembic migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import call, patch
from uuid import UUID

MIGRATION_PATH = (
    Path(__file__).resolve().parents[5]
    / "backend"
    / "migrations"
    / "versions"
    / "20260803_0001_ft001_initial_schema.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ft001_initial_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_is_initial_linear_revision() -> None:
    migration = _load_migration()

    assert migration.revision == "20260803_0001"
    assert migration.down_revision is None


def test_seed_values_are_fixed_and_documented() -> None:
    migration = _load_migration()

    assert UUID("00000000-0000-4000-8000-000000000001") == migration.WORKSPACE_ID
    assert migration.WORKSPACE_NAME == "Trading Workspace V1"
    assert UUID("00000000-0000-4000-8001-000000000001") == migration.XETRA_ID
    assert migration.REFERENCE_VERSION == "FT-001-V1"


def test_upgrade_creates_all_tables_and_seed_rows() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "create_table") as create_table,
        patch.object(migration.op, "create_index") as create_index,
        patch.object(migration.op, "bulk_insert") as bulk_insert,
        patch.object(migration.op, "f", side_effect=lambda name: name),
    ):
        migration.upgrade()

    assert [item.args[0] for item in create_table.call_args_list] == [
        "workspaces",
        "trading_venues",
        "currencies",
        "underlyings",
        "listings",
        "audit_events",
    ]
    assert {item.args[0] for item in create_index.call_args_list} == {
        "ix_underlyings_workspace_lifecycle_name",
        "uq_underlyings_workspace_isin",
        "uq_underlyings_workspace_wkn",
        "ix_listings_underlying_lifecycle",
        "ix_listings_workspace_ticker",
        "uq_listings_active_primary_underlying",
        "ix_audit_events_aggregate_chronology",
        "ix_audit_events_workspace_chronology",
    }
    assert bulk_insert.call_count == 3
    assert bulk_insert.call_args_list[0].args[1][0]["id"] == migration.WORKSPACE_ID
    assert bulk_insert.call_args_list[1].args[1][0]["mic"] == "XETR"
    assert bulk_insert.call_args_list[2].args[1][0]["code"] == "EUR"


def test_downgrade_removes_schema_in_dependency_safe_order() -> None:
    migration = _load_migration()

    with (
        patch.object(migration.op, "drop_index") as drop_index,
        patch.object(migration.op, "drop_table") as drop_table,
    ):
        migration.downgrade()

    assert drop_table.call_args_list == [
        call("audit_events"),
        call("listings"),
        call("underlyings"),
        call("currencies"),
        call("trading_venues"),
        call("workspaces"),
    ]
    assert drop_index.call_count == 8
