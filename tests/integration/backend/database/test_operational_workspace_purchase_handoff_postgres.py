"""PostgreSQL regression for ProductSelection -> BUY -> Operational Workspace handoff."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.features.operational_workspace.service.read_model import OperationalWorkspaceReadModel
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import SqlAlchemyWorkspaceSelectionResolver


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != "trading_workspace_test":
        pytest.fail(
            "Operational Workspace handoff test may run only against trading_workspace_test"
        )
    return url


@pytest.mark.asyncio
async def test_purchase_consumes_current_selection_and_never_reopens_initial_buy() -> None:
    engine = create_async_engine(_test_database_url())
    workspace_id = uuid4()
    underlying_id = uuid4()
    issuer_id = uuid4()
    warrant_id = uuid4()
    terms_id = uuid4()
    listing_id = uuid4()
    trade_plan_id = uuid4()
    trade_plan_version_id = uuid4()
    old_run_id = uuid4()
    current_run_id = uuid4()
    old_evaluation_id = uuid4()
    current_evaluation_id = uuid4()
    old_selection_id = uuid4()
    current_selection_id = uuid4()
    actor = uuid4()
    now = datetime.now(UTC)

    async with engine.connect() as connection:
        outer_transaction = await connection.begin()
        try:
            venue_id = await connection.scalar(
                text("SELECT id FROM trading_venues ORDER BY id LIMIT 1")
            )
            currency_code = await connection.scalar(
                text("SELECT code FROM currencies ORDER BY code LIMIT 1")
            )
            assert venue_id is not None
            assert currency_code is not None

            await connection.execute(
                text("INSERT INTO workspaces (id, name, created_at) VALUES (:id, :name, :now)"),
                {"id": workspace_id, "name": "Workspace purchase handoff", "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO underlyings "
                    "(id, workspace_id, type, name, isin, wkn, lifecycle_status, quality_status, "
                    "version, created_at, updated_at, data_origin) VALUES "
                    "(:id, :workspace_id, 'INDEX', :name, NULL, NULL, 'ACTIVE', 'VERIFIED', "
                    "1, :now, :now, 'MANUAL')"
                ),
                {
                    "id": underlying_id,
                    "workspace_id": workspace_id,
                    "name": "Handoff Underlying",
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO issuers "
                    "(id, legal_name, display_name, country_code, lei, is_active, version, "
                    "created_at, updated_at) VALUES "
                    "(:id, :legal_name, :display_name, 'DE', NULL, true, 1, :now, :now)"
                ),
                {
                    "id": issuer_id,
                    "legal_name": f"Handoff Issuer {issuer_id}",
                    "display_name": "Handoff Issuer",
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO warrants "
                    "(id, workspace_id, issuer_id, underlying_id, product_family, display_name, "
                    "isin, wkn, lifecycle_status, version, created_at, updated_at) VALUES "
                    "(:id, :workspace_id, :issuer_id, :underlying_id, 'WARRANT', :display_name, "
                    "NULL, NULL, 'ACTIVE', 1, :now, :now)"
                ),
                {
                    "id": warrant_id,
                    "workspace_id": workspace_id,
                    "issuer_id": issuer_id,
                    "underlying_id": underlying_id,
                    "display_name": "Handoff Warrant",
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO warrant_terms_versions "
                    "(id, warrant_id, version_no, effective_from, effective_to, option_direction, "
                    "strike, maturity_date, ratio, created_at) VALUES "
                    "(:id, :warrant_id, 1, :now, NULL, 'CALL', 100, :maturity_date, 0.1, :now)"
                ),
                {
                    "id": terms_id,
                    "warrant_id": warrant_id,
                    "maturity_date": date(now.year + 1, 12, 31),
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO warrant_listings "
                    "(id, workspace_id, warrant_id, trading_venue_id, symbol, "
                    "quotation_currency_code, lifecycle_status, version, created_at, updated_at) "
                    "VALUES (:id, :workspace_id, :warrant_id, :venue_id, :symbol, "
                    ":currency_code, 'ACTIVE', 1, :now, :now)"
                ),
                {
                    "id": listing_id,
                    "workspace_id": workspace_id,
                    "warrant_id": warrant_id,
                    "venue_id": venue_id,
                    "symbol": f"HANDOFF-{str(warrant_id)[:8]}",
                    "currency_code": currency_code,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO trade_plans "
                    "(id, workspace_id, underlying_id, origin_type, candidate_id, "
                    "candidate_evaluation_id, created_at, created_by) VALUES "
                    "(:id, :workspace_id, :underlying_id, 'MANUAL', NULL, NULL, :now, 'test')"
                ),
                {
                    "id": trade_plan_id,
                    "workspace_id": workspace_id,
                    "underlying_id": underlying_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO trade_plan_versions "
                    "(id, trade_plan_id, version, direction, thesis, entry_type, entry_currency, "
                    "entry_price, risk_thesis, status, created_at, created_by) VALUES "
                    "(:id, :trade_plan_id, 1, 'LONG', 'Handoff thesis', 'PRICE', :currency_code, "
                    "100, 'Handoff risk', 'APPROVED', :now, 'test')"
                ),
                {
                    "id": trade_plan_version_id,
                    "trade_plan_id": trade_plan_id,
                    "currency_code": currency_code,
                    "now": now,
                },
            )

            for run_id, evaluation_id, selection_id, offset in (
                (old_run_id, old_evaluation_id, old_selection_id, 10),
                (current_run_id, current_evaluation_id, current_selection_id, 2),
            ):
                selected_at = now - timedelta(minutes=offset)
                await connection.execute(
                    text(
                        "INSERT INTO product_selection_runs "
                        "(id, workspace_id, trade_plan_id, trade_plan_version_id, "
                        "trade_plan_version_status, underlying_id, evaluated_at, "
                        "universe_model_id, universe_model_version, eligibility_model_id, "
                        "eligibility_model_version, evaluation_model_id, evaluation_model_version, "
                        "created_at, created_by) "
                        "VALUES (:id, :workspace_id, :trade_plan_id, :trade_plan_version_id, "
                        "'APPROVED', :underlying_id, :evaluated_at, 'FT008', '1', 'FT008', '1', "
                        "'FT008', '1', :evaluated_at, :actor)"
                    ),
                    {
                        "id": run_id,
                        "workspace_id": workspace_id,
                        "trade_plan_id": trade_plan_id,
                        "trade_plan_version_id": trade_plan_version_id,
                        "underlying_id": underlying_id,
                        "evaluated_at": selected_at - timedelta(minutes=1),
                        "actor": actor,
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO product_evaluations "
                        "(id, run_id, warrant_id, warrant_terms_version_id, warrant_listing_id, "
                        "evaluated_at, eligibility_model_id, eligibility_model_version, "
                        "evaluation_model_id, evaluation_model_version, eligibility_status) VALUES "
                        "(:id, :run_id, :warrant_id, :terms_id, :listing_id, :evaluated_at, "
                        "'FT008', '1', 'FT008', '1', 'ELIGIBLE')"
                    ),
                    {
                        "id": evaluation_id,
                        "run_id": run_id,
                        "warrant_id": warrant_id,
                        "terms_id": terms_id,
                        "listing_id": listing_id,
                        "evaluated_at": selected_at - timedelta(minutes=1),
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO product_selections "
                        "(id, run_id, product_evaluation_id, selected_at, selected_by, rationale) "
                        "VALUES (:id, :run_id, :evaluation_id, :selected_at, :actor, :rationale)"
                    ),
                    {
                        "id": selection_id,
                        "run_id": run_id,
                        "evaluation_id": evaluation_id,
                        "selected_at": selected_at,
                        "actor": actor,
                        "rationale": f"Selection {offset}",
                    },
                )

            session_factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            async with session_factory() as session:
                workspace = OperationalWorkspaceReadModel(session)
                before = await workspace._initial_purchase_actions(workspace_id)
                assert [action.resource_id for action in before] == [current_selection_id]

                service = TradePositionService(
                    uow=SqlAlchemyTradePositionUnitOfWork(session),
                    workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
                )
                trade, execution, position = await service.record_initial_purchase(
                    workspace_id=workspace_id,
                    product_selection_id=current_selection_id,
                    quantity=10,
                    price_per_unit=Decimal("2.40"),
                    executed_at=now,
                    actor=actor,
                )

                assert trade.product_selection_id == current_selection_id
                assert trade.product_evaluation_id == current_evaluation_id
                assert execution.trade_id == trade.id
                assert position.trade_id == trade.id
                assert position.open_quantity == 10
                assert not position.is_closed

                after_buy = await workspace.list_actions(workspace_id=workspace_id)
                assert all(action.action_type != "INITIAL_PURCHASE" for action in after_buy)
                open_actions = [
                    action
                    for action in after_buy
                    if action.action_type == "OPEN_POSITION_MANAGEMENT"
                ]
                assert [action.resource_id for action in open_actions] == [trade.id]

                _sale, closed = await service.record_sale(
                    workspace_id=workspace_id,
                    trade_id=trade.id,
                    quantity=10,
                    price_per_unit=Decimal("2.60"),
                    executed_at=now + timedelta(minutes=1),
                    actor=actor,
                )
                assert closed.is_closed
                assert closed.open_quantity == 0

                after_close = await workspace._initial_purchase_actions(workspace_id)
                assert after_close == []
        finally:
            await outer_transaction.rollback()
    await engine.dispose()
