from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


def test_lifecycle_migration_follows_user_preferences_revision() -> None:
    migration = (
        REPOSITORY_ROOT / "backend/migrations/versions/20260806_0005_market_analysis_lifecycle.py"
    ).read_text()
    assert 'revision: str = "20260806_0005"' in migration
    assert 'down_revision: str | None = "20260806_0004"' in migration
    assert '"market_analysis_events"' in migration
    assert '"replacement_version"' in migration
