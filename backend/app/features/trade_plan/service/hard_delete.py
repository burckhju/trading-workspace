"""Explicit user-owned hard delete for one TradePlan and its dependent history."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class TradePlanDeletionSummary:
    trade_plan_id: UUID
    trade_plan_versions: int
    product_selection_runs: int
    trades: int
    positions: int
    alerts: int
    notifications: int
    post_trade_observations: int
    exit_reviews: int
    trade_journals: int
    learning_evidence: int
    external_observation_trade_links: int


class TradePlanHardDeleteService:
    """Delete a user-owned TradePlan graph without deleting shared reference data."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete(self, *, workspace_id: UUID, trade_plan_id: UUID) -> TradePlanDeletionSummary:
        plan = await self._session.execute(
            text(
                "SELECT id FROM trade_plans "
                "WHERE id = :trade_plan_id AND workspace_id = :workspace_id"
            ),
            {"trade_plan_id": trade_plan_id, "workspace_id": workspace_id},
        )
        if plan.scalar_one_or_none() is None:
            raise ValueError("trade plan not found")

        await self._session.execute(text("SET CONSTRAINTS ALL DEFERRED"))

        version_ids = await self._ids(
            "SELECT id FROM trade_plan_versions WHERE trade_plan_id = :id", trade_plan_id
        )
        run_ids = await self._ids(
            "SELECT id FROM product_selection_runs WHERE trade_plan_id = :id", trade_plan_id
        )
        evaluation_ids = await self._ids_for_parent(
            "SELECT id FROM product_evaluations WHERE run_id IN :ids", run_ids
        )
        selection_ids = await self._ids_for_parent(
            "SELECT id FROM product_selections WHERE run_id IN :ids", run_ids
        )
        trade_ids = await self._ids(
            "SELECT id FROM trades WHERE trade_plan_id = :id", trade_plan_id
        )
        position_ids = await self._ids_for_parent(
            "SELECT id FROM positions WHERE trade_id IN :ids", trade_ids
        )
        alert_ids = await self._ids_for_parent(
            "SELECT id FROM alerts WHERE trade_id IN :ids", trade_ids
        )
        notification_ids = await self._ids_for_parent(
            "SELECT id FROM notifications WHERE alert_id IN :ids", alert_ids
        )
        observation_ids = await self._ids_for_parent(
            "SELECT id FROM post_trade_observations WHERE trade_id IN :ids", trade_ids
        )
        exit_review_ids = await self._ids_for_parent(
            "SELECT id FROM exit_reviews WHERE post_trade_observation_id IN :ids", observation_ids
        )
        exit_review_version_ids = await self._ids_for_parent(
            "SELECT id FROM exit_review_versions WHERE exit_review_id IN :ids", exit_review_ids
        )
        journal_ids = await self._ids_for_parent(
            "SELECT id FROM trade_journals WHERE trade_id IN :ids", trade_ids
        )
        journal_version_ids = await self._ids_for_parent(
            "SELECT id FROM trade_journal_versions WHERE trade_journal_id IN :ids", journal_ids
        )
        link_ids = await self._ids_for_parent(
            "SELECT DISTINCT external_observation_trade_link_id "
            "FROM external_observation_trade_link_versions WHERE trade_id IN :ids",
            trade_ids,
        )

        ft011_evidence_ids = await self._ids_for_parent(
            "SELECT learning_evidence_id FROM ft011_evidence WHERE trade_id IN :ids", trade_ids
        )
        journal_evidence_ids = await self._ids_for_parent(
            "SELECT learning_evidence_id FROM trade_journal_version_evidence "
            "WHERE trade_journal_version_id IN :ids",
            journal_version_ids,
        )
        learning_evidence_ids = tuple(dict.fromkeys((*ft011_evidence_ids, *journal_evidence_ids)))
        lesson_link_ids = await self._ids_for_parent(
            "SELECT id FROM lesson_evidence_links WHERE learning_evidence_id IN :ids",
            learning_evidence_ids,
        )

        await self._delete_in(
            "lesson_review_signal_evidence", "lesson_evidence_link_id", lesson_link_ids
        )
        await self._delete_in(
            "lesson_evidence_links", "learning_evidence_id", learning_evidence_ids
        )
        await self._delete_in("ft011_evidence", "learning_evidence_id", learning_evidence_ids)
        await self._delete_in(
            "trade_journal_version_evidence", "learning_evidence_id", learning_evidence_ids
        )
        await self._delete_in("learning_evidence", "id", learning_evidence_ids)

        await self._delete_in("exit_review_versions", "id", exit_review_version_ids)
        await self._delete_in("exit_reviews", "id", exit_review_ids)
        await self._delete_in("post_trade_observations", "id", observation_ids)

        await self._delete_in("trade_journal_versions", "id", journal_version_ids)
        await self._delete_in("trade_journals", "id", journal_ids)

        await self._delete_in(
            "external_observation_trade_link_versions",
            "external_observation_trade_link_id",
            link_ids,
        )
        await self._delete_in("external_observation_trade_links", "id", link_ids)

        await self._delete_in("notification_delivery_attempts", "notification_id", notification_ids)
        await self._delete_in("notifications", "id", notification_ids)
        await self._delete_in("monitoring_rule_states", "position_id", position_ids)
        await self._delete_in("alerts", "id", alert_ids)
        await self._delete_in("trade_management_events", "trade_id", trade_ids)
        await self._delete_in("execution_records", "trade_id", trade_ids)
        await self._delete_in("positions", "id", position_ids)
        await self._delete_in("trades", "id", trade_ids)

        await self._delete_in("product_selections", "id", selection_ids)
        await self._delete_in("product_evaluation_inputs", "product_evaluation_id", evaluation_ids)
        await self._delete_in(
            "product_evaluation_criteria", "product_evaluation_id", evaluation_ids
        )
        await self._delete_in("product_evaluation_metrics", "product_evaluation_id", evaluation_ids)
        await self._delete_in("product_evaluation_reasons", "product_evaluation_id", evaluation_ids)
        await self._delete_in("product_evaluations", "id", evaluation_ids)
        await self._delete_in("product_universe_omissions", "run_id", run_ids)
        await self._delete_in("product_selection_runs", "id", run_ids)

        await self._delete_in("trade_plan_approvals", "trade_plan_version_id", version_ids)
        await self._delete_in("trade_plan_events", "trade_plan_id", (trade_plan_id,))
        await self._delete_in("trade_plan_targets", "trade_plan_version_id", version_ids)
        await self._delete_in("trade_plan_versions", "id", version_ids)
        await self._delete_in("trade_plans", "id", (trade_plan_id,))

        await self._session.commit()
        return TradePlanDeletionSummary(
            trade_plan_id=trade_plan_id,
            trade_plan_versions=len(version_ids),
            product_selection_runs=len(run_ids),
            trades=len(trade_ids),
            positions=len(position_ids),
            alerts=len(alert_ids),
            notifications=len(notification_ids),
            post_trade_observations=len(observation_ids),
            exit_reviews=len(exit_review_ids),
            trade_journals=len(journal_ids),
            learning_evidence=len(learning_evidence_ids),
            external_observation_trade_links=len(link_ids),
        )

    async def _ids(self, statement: str, id_value: UUID) -> tuple[UUID, ...]:
        result = await self._session.execute(text(statement), {"id": id_value})
        return tuple(result.scalars().all())

    async def _ids_for_parent(self, statement: str, ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if not ids:
            return ()
        query = text(statement).bindparams(bindparam("ids", expanding=True))
        result = await self._session.execute(query, {"ids": ids})
        return tuple(result.scalars().all())

    async def _delete_in(self, table: str, column: str, ids: tuple[UUID, ...]) -> None:
        if not ids:
            return
        statement = text(f"DELETE FROM {table} WHERE {column} IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        await self._session.execute(statement, {"ids": ids})
