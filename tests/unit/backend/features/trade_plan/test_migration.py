from pathlib import Path


def test_trade_plan_migration_contains_versioned_product_neutral_schema() -> None:
    migration = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260811_0008_ft007_trade_plan_persistence.py"
    ).read_text()
    assert '"trade_plans"' in migration
    assert '"trade_plan_versions"' in migration
    assert '"trade_plan_targets"' in migration
    assert '"trade_plan_events"' in migration
    assert '"trade_plan_approvals"' in migration
    assert "uq_trade_plan_versions_plan_version" in migration
    assert "uq_trade_plan_approvals_version" in migration
    assert "candidate_evaluation_id" in migration
    assert "direction = 'LONG'" in migration
    for forbidden in (
        "warrant_id",
        "issuer_id",
        "leverage",
        "spread",
        "order_quantity",
    ):
        assert forbidden not in migration
