from pathlib import Path

from sqlalchemy import Boolean, Integer, String, UniqueConstraint

from app.features.market.persistence.models import IssuerModel


def test_issuer_model_is_global_provider_neutral_reference_data() -> None:
    table = IssuerModel.__table__

    assert table.name == "issuers"
    assert set(table.columns.keys()) == {
        "id",
        "legal_name",
        "display_name",
        "country_code",
        "lei",
        "is_active",
        "version",
        "created_at",
        "updated_at",
    }
    assert "workspace_id" not in table.columns
    assert "underlying_id" not in table.columns
    assert "trading_venue_id" not in table.columns
    assert "provider_issuer_id" not in table.columns

    assert isinstance(table.c.legal_name.type, String)
    assert isinstance(table.c.display_name.type, String)
    assert isinstance(table.c.is_active.type, Boolean)
    assert isinstance(table.c.version.type, Integer)
    assert table.c.country_code.nullable is True
    assert table.c.lei.nullable is True

    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("lei",) in unique_columns


def test_ft003_migration_creates_only_issuer_reference_data() -> None:
    migration = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260815_0010_ft003_issuer_persistence.py"
    ).read_text()

    assert 'down_revision: str | None = "20260813_0009"' in migration
    assert 'op.create_table(\n        "issuers"' in migration
    assert 'sa.Column("id", sa.Uuid(), nullable=False)' in migration
    assert 'sa.Column("lei", sa.String(length=20), nullable=True)' in migration
    assert 'sa.UniqueConstraint("lei", name="uq_issuers_lei")' in migration
    assert "ck_issuers_legal_name_not_blank" in migration
    assert "ck_issuers_display_name_not_blank" in migration
    assert "ck_issuers_country_code_iso_shape" in migration
    assert "ck_issuers_lei_canonical_shape" in migration
    assert "ck_issuers_version_positive" in migration

    for forbidden in (
        "workspace_id",
        "underlying_id",
        "trading_venue_id",
        "provider_issuer_id",
        "warrant_id",
        'op.create_table(\n        "warrants"',
    ):
        assert forbidden not in migration
