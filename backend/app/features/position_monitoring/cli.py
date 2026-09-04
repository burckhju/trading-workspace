from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.core.di import ApplicationContainer
from app.features.position_monitoring.bootstrap import build_position_monitoring_runtime
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run exactly one persisted position-monitoring cycle "
            "for operational smoke testing."
        ),
    )
    parser.add_argument(
        "--allow-telegram",
        action="store_true",
        help="Explicitly allow configured Telegram delivery during this live smoke run.",
    )
    parser.add_argument("--expect-alerts", type=int)
    parser.add_argument("--expect-deliveries", type=int)
    parser.add_argument("--expect-delivery-failures", type=int)
    return parser


def summarize(result: PositionMonitoringRuntimeResult) -> dict[str, int]:
    cycle = asdict(result.cycle)
    return {
        "positions_seen": int(cycle["positions_seen"]),
        "positions_checked": int(cycle["positions_checked"]),
        "rules_evaluated": int(cycle["rules_evaluated"]),
        "alerts_created": int(cycle["alerts_created"]),
        "alerts_deduplicated": int(cycle["alerts_deduplicated"]),
        "alerts_resolved": int(cycle["alerts_resolved"]),
        "missing_market_data": int(cycle["missing_market_data"]),
        "stale_market_data": int(cycle["stale_market_data"]),
        "market_data_errors": int(cycle["market_data_errors"]),
        "position_errors": int(cycle["position_errors"]),
        "notifications_created": result.notifications_created,
        "notifications_delivered": result.notifications_delivered,
        "notification_failures": result.notification_failures,
    }


def validate_expectations(
    summary: dict[str, int],
    *,
    expect_alerts: int | None,
    expect_deliveries: int | None,
    expect_delivery_failures: int | None,
) -> list[str]:
    expectations = {
        "alerts_created": expect_alerts,
        "notifications_delivered": expect_deliveries,
        "notification_failures": expect_delivery_failures,
    }
    return [
        f"{key}: expected {expected}, got {summary[key]}"
        for key, expected in expectations.items()
        if expected is not None and summary[key] != expected
    ]


async def run_once(*, allow_telegram: bool) -> PositionMonitoringRuntimeResult:
    settings = get_settings()
    telegram = settings.notification.telegram
    if telegram.enabled and not allow_telegram:
        raise RuntimeError(
            "Telegram delivery is configured. Re-run with --allow-telegram to permit a real send."
        )

    container = ApplicationContainer.build(settings)
    try:
        runtime = build_position_monitoring_runtime(
            settings=settings,
            database=container.database,
            market_data=container.require_eodhd_adapter(),
        )
        return await runtime.run()
    finally:
        await container.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = asyncio.run(run_once(allow_telegram=args.allow_telegram))
    except RuntimeError as error:
        parser.error(str(error))

    summary = summarize(result)
    print(json.dumps(summary, sort_keys=True))
    failures = validate_expectations(
        summary,
        expect_alerts=args.expect_alerts,
        expect_deliveries=args.expect_deliveries,
        expect_delivery_failures=args.expect_delivery_failures,
    )
    if failures:
        parser.error("; ".join(failures))


if __name__ == "__main__":
    main()
