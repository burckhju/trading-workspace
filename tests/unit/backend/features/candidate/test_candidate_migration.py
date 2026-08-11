from pathlib import Path


def test_candidate_migration_contains_immutable_evaluation_schema() -> None:
    migration = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260808_0006_top_down_candidates.py"
    ).read_text()
    assert '"candidate_evaluations"' in migration
    assert '"candidate_evaluation_sources"' in migration
    assert '"candidate_criterion_results"' in migration
    assert "uq_candidate_evaluations_candidate_version" in migration
