from pathlib import Path


def test_source_resolution_migration_contains_semantic_bridges() -> None:
    migration = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260810_0007_top_down_source_resolution.py"
    ).read_text()
    assert '"underlying_benchmark_assignments"' in migration
    assert '"market_reference_listing_assignments"' in migration
    assert "ix_underlying_benchmark_assignments_underlying_role_valid" in migration
    assert "ix_market_reference_listing_assignments_reference_valid" in migration
