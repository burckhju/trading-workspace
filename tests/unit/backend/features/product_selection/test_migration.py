from pathlib import Path


def test_ft008_migration_is_based_on_warrant_release_head_and_preserves_snapshots():
    text = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260816_0012_ft008_product_selection_persistence.py"
    ).read_text()
    assert 'down_revision: str | None = "20260815_0011"' in text
    for table in (
        "product_selection_runs",
        "product_evaluations",
        "product_evaluation_inputs",
        "product_evaluation_criteria",
        "product_evaluation_metrics",
        "product_evaluation_reasons",
        "product_universe_omissions",
        "product_selections",
    ):
        assert f'"{table}"' in text
    for ref in (
        "trade_plan_version_id",
        "warrant_id",
        "warrant_terms_version_id",
        "warrant_listing_id",
    ):
        assert ref in text
    assert "trade_plan_version_status = 'APPROVED'" in text
    assert "fk_product_selections_evaluation_same_run" in text
    for forbidden in ("order_quantity", "position_size", "broker_order_id"):
        assert forbidden not in text
