from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


def test_user_preferences_migration_is_additive_and_scoped() -> None:
    migration = (
        REPOSITORY_ROOT / "backend/migrations/versions/20260806_0004_user_preferences.py"
    ).read_text()
    assert 'down_revision: str | None = "20260805_0003"' in migration
    assert '"user_preferences"' in migration
    assert '"actor_id"' in migration
    assert "uq_user_preferences_scope_name" in migration
