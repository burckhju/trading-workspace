"""Unit tests for FT-011 review-input fingerprint."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.features.post_trade.application.input_fingerprint import (
    build_exit_review_input_fingerprint,
)
from app.features.post_trade.application.ports import (
    DailyObservation,
    PlanningContext,
    TradeExitContext,
)
from app.features.post_trade.domain.observation_metrics import (
    build_observation_evidence,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _inputs():
    workspace_id = uuid4()
    trade_id = uuid4()
    listing_id = uuid4()

    trade = TradeExitContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        product_id=uuid4(),
        is_fully_closed=True,
        full_exit_at=NOW,
        realized_gross_pnl=Decimal("100"),
        executions=(),
        management_events=(),
    )

    planning = PlanningContext(
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        original_stop=Decimal("90"),
        original_targets=(Decimal("110"),),
    )

    evidence = build_observation_evidence(
        (
            DailyObservation(
                listing_id=listing_id,
                trading_date=date(2026, 8, 19),
                open=Decimal("100"),
                high=Decimal("115"),
                low=Decimal("95"),
                close=Decimal("110"),
                adjusted_close=None,
                quality_status="VALID",
            ),
        ),
        full_exit_at=NOW,
        target_count=20,
        targets=planning.original_targets,
        stop=planning.original_stop,
    )

    return trade, planning, evidence


def test_fingerprint_is_deterministic() -> None:
    trade, planning, evidence = _inputs()

    first = build_exit_review_input_fingerprint(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )
    second = build_exit_review_input_fingerprint(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )

    assert first == second
    assert len(first) == 64


def test_changed_trade_fact_changes_fingerprint() -> None:
    trade, planning, evidence = _inputs()

    original = build_exit_review_input_fingerprint(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )

    changed = TradeExitContext(
        workspace_id=trade.workspace_id,
        trade_id=trade.trade_id,
        product_id=trade.product_id,
        is_fully_closed=trade.is_fully_closed,
        full_exit_at=trade.full_exit_at,
        realized_gross_pnl=Decimal("101"),
        executions=trade.executions,
        management_events=trade.management_events,
    )

    assert original != build_exit_review_input_fingerprint(
        trade=changed,
        planning=planning,
        evidence=evidence,
    )


def test_changed_planning_fact_changes_fingerprint() -> None:
    trade, planning, evidence = _inputs()

    original = build_exit_review_input_fingerprint(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )

    changed = PlanningContext(
        trade_plan_id=planning.trade_plan_id,
        trade_plan_version_id=planning.trade_plan_version_id,
        original_stop=Decimal("89"),
        original_targets=planning.original_targets,
    )

    assert original != build_exit_review_input_fingerprint(
        trade=trade,
        planning=changed,
        evidence=evidence,
    )
