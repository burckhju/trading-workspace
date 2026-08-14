from pathlib import Path


def test_ft002_migration_hardens_existing_trading_venue_identity() -> None:
    migration = (
        Path(__file__).parents[5]
        / "backend/migrations/versions/20260813_0009_ft002_trading_venue_persistence.py"
    ).read_text()

    assert 'down_revision: str | None = "20260811_0008"' in migration
    assert 'op.add_column("trading_venues"' in migration
    assert "UPDATE trading_venues SET mic = upper(trim(mic)), version = 1" in migration
    assert "ck_trading_venues_mic_uppercase" in migration
    assert "ck_trading_venues_version_positive" in migration
    assert 'op.alter_column("audit_events", "workspace_id"' in migration
    assert "DELETE FROM audit_events" in migration
    assert "aggregate_type = 'TRADING_VENUE'" in migration

    for forbidden in (
        'op.create_table("trading_venues"',
        "provider_exchange_code",
        "issuer_id",
        "currency_code",
        "warrant_id",
    ):
        assert forbidden not in migration
