from pathlib import Path

MIGRATION = (
    Path(__file__).parents[5]
    / "backend/migrations/versions/20260903_0030_position_monitoring_alert_notification.py"
)


def test_monitoring_migration_follows_current_head() -> None:
    text = MIGRATION.read_text()
    assert 'revision: str = "20260903_0030"' in text
    assert 'down_revision: str | None = "20260828_0029"' in text


def test_monitoring_migration_separates_alert_notification_and_delivery() -> None:
    text = MIGRATION.read_text()
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
