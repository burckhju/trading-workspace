from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.features.position_monitoring.domain.models import MonitoringRule, MonitoringRuleType
from app.features.trade_position.domain.enums import TradeManagementEventType
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.tools import confirm_warrant_rules as tool


@pytest.fixture
def plan():
    trade, position, warrant = uuid4(), uuid4(), uuid4()
    return tool.ConfirmationPlan(
        workspace_id=uuid4(),
        currency="EUR",
        positions_count=1,
        rules=tuple(
            tool.RuleConfirmation(
                trade_id=trade,
                position_id=position,
                warrant_id=warrant,
                isin="DE000VH2LU21",
                product_name="UNH warrant",
                rule_key=key,
                threshold=value,
                already_confirmed=False,
            )
            for key, value in (("CURRENT_STOP", ".16"), ("CURRENT_TARGET", "2.50"))
        ),
    )


def test_roundtrip_preserves_prices_and_replay_skips_confirmed_rules(plan):
    restored = tool.ConfirmationPlan.model_validate_json(plan.model_dump_json())
    assert restored == plan
    assert tool.pending_confirmations(plan, restored) == plan.rules
    confirmed = plan.model_copy(
        update={
            "rules": tuple(r.model_copy(update={"already_confirmed": True}) for r in plan.rules)
        }
    )
    assert tool.pending_confirmations(plan, confirmed) == ()
    with pytest.raises(ValueError, match="PLAN_CHANGED"):
        tool.pending_confirmations(confirmed, plan)


@pytest.mark.parametrize("field", ["threshold", "warrant_id", "position_id", "trade_id", "isin"])
def test_changed_values_and_identities_require_new_preview(plan, field):
    value = Decimal("3") if field == "threshold" else "another" if field == "isin" else uuid4()
    changed = plan.model_copy(
        update={"rules": (plan.rules[0].model_copy(update={field: value}), plan.rules[1])}
    )
    with pytest.raises(ValueError, match="PLAN_CHANGED"):
        tool.pending_confirmations(plan, changed)


@pytest.mark.parametrize("change", [{"currency": "USD"}, {"workspace_id": uuid4()}])
def test_scope_change_is_rejected(plan, change):
    with pytest.raises(ValueError, match="PLAN_CHANGED"):
        tool.pending_confirmations(plan, plan.model_copy(update=change))


@pytest.mark.parametrize("invalid", ["duplicate", "missing", "extra", "currency", "price"])
def test_plan_rejects_ambiguous_or_malformed_content(plan, invalid):
    payload = plan.model_dump(mode="json")
    if invalid == "duplicate":
        payload["rules"][1] = payload["rules"][0]
    elif invalid == "missing":
        payload["rules"].pop()
    elif invalid == "extra":
        payload["force"] = True
    elif invalid == "currency":
        payload["currency"] = "eur"
    else:
        payload["rules"][0]["threshold"] = "NaN"
    with pytest.raises(ValidationError):
        tool.ConfirmationPlan.model_validate(payload)


@pytest.fixture
def preview_context(monkeypatch, plan):
    subject = SimpleNamespace(
        trade_id=plan.rules[0].trade_id,
        position_id=plan.rules[0].position_id,
        warrant_id=plan.rules[0].warrant_id,
        rules=(
            MonitoringRule("CURRENT_STOP", MonitoringRuleType.STOP_REACHED, Decimal(".16")),
            MonitoringRule("CURRENT_TARGET", MonitoringRuleType.TARGET_REACHED, Decimal("2.50")),
        ),
    )
    resolution = SimpleNamespace(subject=subject, position_id=subject.position_id, issue=None)
    reader = AsyncMock()
    reader.list_resolutions.return_value = (resolution,)
    monkeypatch.setattr(tool, "SqlAlchemyMonitoringSubjectReader", lambda *a, **kw: reader)
    events = AsyncMock()
    events.list_effective_for_trade.return_value = []
    monkeypatch.setattr(tool, "SqlAlchemyTradeManagementEventRepository", lambda s: events)
    session = AsyncMock()
    session.scalar.return_value = SimpleNamespace(isin="DE000VH2LU21", display_name="UNH warrant")
    return SimpleNamespace(
        reader=reader, events=events, session=session, subject=subject, resolution=resolution
    )


async def test_preview_has_no_writes_or_provider_dependencies(plan, preview_context):
    result = await tool.preview(
        preview_context.session,
        workspace_id=plan.workspace_id,
        currency="EUR",
        expect_positions=1,
    )
    assert result == plan
    preview_context.session.commit.assert_not_called()
    preview_context.events.add.assert_not_called()


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("empty", "OPEN_POSITION_COUNT_MISMATCH"),
        ("count", "OPEN_POSITION_COUNT_MISMATCH"),
        ("unresolved", "UNRESOLVED_POSITION"),
        ("identity", "WARRANT_IDENTITY_MISSING"),
        ("future", "FUTURE_PRICE_EVENTS"),
        ("binding", "CONFLICTING_PRICE_BINDING"),
        ("no_target", "exactly one stop"),
    ],
)
async def test_preview_fails_closed_for_incomplete_or_conflicting_data(
    plan, preview_context, case, reason
):
    ctx = preview_context
    if case == "empty":
        ctx.reader.list_resolutions.return_value = ()
    elif case == "unresolved":
        ctx.resolution.subject = None
    elif case == "identity":
        ctx.session.scalar.return_value = None
    elif case == "future":
        ctx.events.list_effective_for_trade.return_value = [
            SimpleNamespace(
                effective_at=datetime.now(UTC) + timedelta(days=1),
                event_type=TradeManagementEventType.STOP_CHANGED,
            )
        ]
    elif case == "binding":
        ctx.subject.rules = (
            MonitoringRule(
                "CURRENT_STOP",
                MonitoringRuleType.STOP_REACHED,
                Decimal(".16"),
                PriceBinding(PriceBasis.UNDERLYING, uuid4(), "USD"),
            ),
        )
    elif case == "no_target":
        ctx.subject.rules = ctx.subject.rules[:1]
    with pytest.raises(ValueError, match=reason):
        await tool.preview(
            ctx.session,
            workspace_id=plan.workspace_id,
            currency="EUR",
            expect_positions=2 if case == "count" else 1,
        )


async def test_apply_requires_explicit_actor_before_opening_database(plan, monkeypatch):
    args = tool.build_parser().parse_args(
        ["apply", "--workspace-id", str(plan.workspace_id), "--currency", "EUR"]
    )
    monkeypatch.setattr(tool, "DatabaseManager", lambda s: pytest.fail("database opened"))
    with pytest.raises(ValueError, match="actor-id"):
        await tool.run(args)


async def test_apply_rejects_plan_scope_before_locking(plan):
    connection = SimpleNamespace(in_transaction=lambda: True, execute=AsyncMock())
    with pytest.raises(ValueError, match="PLAN_SCOPE_MISMATCH"):
        await tool.apply_plan(
            connection, plan=plan, workspace_id=uuid4(), currency="EUR", actor=uuid4()
        )
    connection.execute.assert_not_called()
