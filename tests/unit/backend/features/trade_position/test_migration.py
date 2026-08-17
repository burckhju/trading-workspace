from pathlib import Path

MIGRATION = (
    Path(__file__).parents[5]
    / "backend/migrations/versions/20260817_0014_ft009_trade_position_persistence.py"
)


def test_ft009_migration_follows_current_repository_head() -> None:
    text = MIGRATION.read_text()

    assert 'revision: str = "20260817_0014"' in text
    assert 'down_revision: str | None = "20260816_0013"' in text


def test_ft009_migration_creates_core_tables() -> None:
    text = MIGRATION.read_text()

    for table in (
        "trades",
        "execution_records",
        "positions",
    ):
        assert f'"{table}"' in text


def test_ft009_migration_keeps_trade_execution_and_position_separate() -> None:
    text = MIGRATION.read_text()

    for field in (
        "trade_id",
        "product_id",
        "quantity",
        "price_per_unit",
        "executed_at",
        "recorded_at",
        "open_quantity",
        "cost_basis",
        "average_entry_price",
    ):
        assert field in text


def test_ft009_migration_preserves_workspace_selection_provenance() -> None:
    text = MIGRATION.read_text()

    for field in (
        "trade_plan_id",
        "trade_plan_version_id",
        "product_selection_id",
        "product_evaluation_id",
    ):
        assert field in text


def test_ft009_migration_does_not_add_out_of_scope_order_fields() -> None:
    text = MIGRATION.read_text()

    for forbidden in (
        "broker_order_id",
        "order_status",
        "position_size",
        "commission",
        "fee",
        "tax",
    ):
        assert forbidden not in text


FT010_MIGRATION = (
    Path(__file__).parents[5]
    / "backend/migrations/versions/20260817_0015_ft010_execution_side.py"
)


def test_ft010_execution_side_migration_follows_ft009_head() -> None:
    text = FT010_MIGRATION.read_text()

    assert 'revision: str = "20260817_0015"' in text
    assert 'down_revision: str | None = "20260817_0014"' in text


def test_ft010_execution_side_migration_backfills_historical_rows_as_buy() -> None:
    text = FT010_MIGRATION.read_text()

    assert '"side"' in text
    assert 'server_default="BUY"' in text
    assert "side IN ('BUY', 'SELL')" in text
    assert 'server_default=None' in text


FT010_SUPERSESSION_MIGRATION = (
    Path(__file__).parents[5]
    / "backend/migrations/versions/20260817_0016_ft010_execution_supersession.py"
)


def test_ft010_supersession_migration_follows_execution_side() -> None:
    text = FT010_SUPERSESSION_MIGRATION.read_text()

    assert 'revision: str = "20260817_0016"' in text
    assert 'down_revision: str | None = "20260817_0015"' in text


def test_ft010_supersession_migration_preserves_original_execution() -> None:
    text = FT010_SUPERSESSION_MIGRATION.read_text()

    assert '"supersedes_execution_id"' in text
    assert '"fk_execution_records_supersedes"' in text
    assert '"uq_execution_records_supersedes"' in text
    assert 'ondelete="RESTRICT"' in text
