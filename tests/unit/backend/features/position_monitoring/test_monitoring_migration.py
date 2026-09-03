from pathlib import Path

VERSIONS = Path(__file__).parents[5] / "backend/migrations/versions"
MONITORING_MIGRATION = VERSIONS / "20260903_0030_position_monitoring_alert_notification.py"
RECOVERY_MIGRATION = VERSIONS / "20260903_0031_notification_delivery_recovery.py"


def test_monitoring_migrations_follow_current_head() -> None:
    monitoring = MONITORING_MIGRATION.read_text()
    recovery = RECOVERY_MIGRATION.read_text()
    assert 'revision: str = "20260903_0030"' in monitoring
    assert 'down_revision: str | None = "20260828_0029"' in monitoring
    assert 'revision: str = "20260903_0031"' in recovery
    assert 'down_revision: str | None = "20260903_0030"' in recovery
    assert "IN_PROGRESS" in recovery


def test_monitoring_migration_separates_alert_notification_and_delivery() -> None:
    text = MONITORING_MIGRATION.read_text()
    for table in (
        "alerts",
        "monitoring_rule_states",
        "notifications",
        "notification_delivery_attempts",
    ):
        assert f'"{table}"' in text
    assert "uq_monitoring_rule_state_position_rule" in text
    assert "uq_notification_alert_channel_destination" in text
    assert "uq_delivery_attempt_number" in text
