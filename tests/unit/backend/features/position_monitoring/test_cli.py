from app.features.position_monitoring.cli import (
    build_parser,
    summarize,
    validate_expectations,
)
from app.features.position_monitoring.service.cycle import MonitoringCycleResult
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult


def result() -> PositionMonitoringRuntimeResult:
    return PositionMonitoringRuntimeResult(
        cycle=MonitoringCycleResult(
            positions_seen=2,
            positions_checked=2,
            rules_evaluated=4,
            alerts_created=1,
            alerts_deduplicated=1,
            alerts_resolved=0,
            subject_errors=0,
            missing_market_data=0,
            stale_market_data=0,
            market_data_errors=0,
            position_errors=0,
            alerts=(),
            created_alerts=(),
        ),
        notifications_created=1,
        notifications_delivered=1,
        notification_failures=0,
    )


def test_smoke_summary_contains_only_operational_counts() -> None:
    summary = summarize(result())

    assert summary["positions_seen"] == 2
    assert summary["alerts_created"] == 1
    assert summary["notifications_delivered"] == 1
    assert "alerts" not in summary


def test_expectation_validation_reports_mismatches() -> None:
    summary = summarize(result())

    failures = validate_expectations(
        summary,
        expect_alerts=0,
        expect_deliveries=1,
        expect_delivery_failures=1,
    )

    assert failures == [
        "alerts_created: expected 0, got 1",
        "notification_failures: expected 1, got 0",
    ]


def test_parser_requires_explicit_flag_only_when_operator_supplies_it() -> None:
    parser = build_parser()

    args = parser.parse_args(["--allow-telegram", "--expect-alerts", "1"])

    assert args.allow_telegram is True
    assert args.expect_alerts == 1
