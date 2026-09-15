from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import AsyncExitStack
from dataclasses import asdict

import httpx

from app.core.config import get_settings
from app.core.di import ApplicationContainer
from app.features.position_monitoring.backend_valuations import (
    BackendProductValuations,
    backend_origin,
)
from app.features.position_monitoring.bootstrap import build_position_monitoring_runtime
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_runtime import build_warrant_quote_resolver
from app.features.position_monitoring.service.rule_prices import ProductValuationReader
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult


def build_parser() -> argparse.ArgumentParser:
    description = (
        "Run exactly one persisted position-monitoring cycle " "for operational smoke testing."
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--allow-telegram",
        action="store_true",
        help="Explicitly allow configured Telegram delivery during this live smoke run.",
    )
    parser.add_argument("--expect-alerts", type=int)
    parser.add_argument("--expect-deliveries", type=int)
    parser.add_argument("--expect-delivery-failures", type=int)
    parser.add_argument(
        "--backend-url",
        type=backend_origin,
        help="Use product valuations from the running backend and its shared quote cache/budget.",
    )
    parser.add_argument(
        "--include-rule-checks",
        action="store_true",
        help="Include per-rule results and backend product-source diagnostics in JSON output.",
    )
    return parser


def summarize(result: PositionMonitoringRuntimeResult) -> dict[str, int]:
    cycle = asdict(result.cycle)
    return {
        "positions_seen": int(cycle["positions_seen"]),
        "positions_checked": int(cycle["positions_checked"]),
        "rules_evaluated": int(cycle["rules_evaluated"]),
        "blocked_rules": int(cycle["blocked_rules"]),
        "subject_errors": int(cycle["subject_errors"]),
        "alerts_invalidated": result.alerts_invalidated,
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


async def run_once(
    *,
    allow_telegram: bool,
    backend_url: str | None = None,
    quote_diagnostics: list[dict[str, object]] | None = None,
) -> PositionMonitoringRuntimeResult:
    settings = get_settings()
    telegram = settings.notification.telegram
    if telegram.enabled and not allow_telegram:
        raise RuntimeError(
            "Telegram delivery is configured. Re-run with --allow-telegram to permit a real send."
        )

    container = ApplicationContainer.build(settings)
    try:
        async with AsyncExitStack() as stack:
            products: ProductValuationReader
            if backend_url is not None:
                client = await stack.enter_async_context(
                    httpx.AsyncClient(
                        base_url=backend_origin(backend_url),
                        timeout=60,
                        follow_redirects=False,
                        trust_env=False,
                    )
                )
                remote = BackendProductValuations(client, diagnostics=quote_diagnostics)
                await remote.check_ready()
                products = remote
            else:
                products = ProductPositionValuationService(
                    database=container.database,
                    quote_resolver=build_warrant_quote_resolver(container),
                )
            runtime = build_position_monitoring_runtime(
                settings=settings,
                database=container.database,
                market_data=container.eodhd.adapter if container.eodhd else None,
                products=products,
            )
            return await runtime.run()
    finally:
        await container.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    quote_diagnostics: list[dict[str, object]] = []
    try:
        result = asyncio.run(
            run_once(
                allow_telegram=args.allow_telegram,
                backend_url=args.backend_url,
                quote_diagnostics=quote_diagnostics if args.include_rule_checks else None,
            )
        )
    except RuntimeError as error:
        parser.error(str(error))

    summary = summarize(result)
    output: dict[str, object] = {
        **summary,
        "quote_context": "RUNNING_BACKEND" if args.backend_url else "ISOLATED_PROCESS_CACHE",
    }
    if args.include_rule_checks:
        output["rule_checks"] = result.cycle.rule_checks
        output["product_valuations"] = quote_diagnostics
    print(json.dumps(output, sort_keys=True))
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
