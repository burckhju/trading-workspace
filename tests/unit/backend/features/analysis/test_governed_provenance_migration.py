from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


def test_governed_provenance_migration_follows_ft013() -> None:
    migration = (
        REPOSITORY_ROOT
        / "backend/migrations/versions/20260825_0024_ft006_governed_model_provenance.py"
    ).read_text()

    assert 'revision = "20260825_0024"' in migration
    assert 'down_revision = "20260825_0023"' in migration
    assert '"governed_model_version_id"' in migration
    assert '"governed_model_versions"' in migration
    assert 'ondelete="RESTRICT"' in migration
