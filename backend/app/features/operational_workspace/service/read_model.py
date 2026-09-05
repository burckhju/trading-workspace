"""Server-side operational action projection over existing owner features."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import AlertStatus, AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.candidate.domain.enums import CandidateStatus
from app.features.candidate.persistence.models import CandidateModel
from app.features.candidate.service.runtime_readiness import (
    RuntimeAwareCandidateLiveWorkflowService,
)
from app.features.notification.domain.models import NotificationStatus
from app.features.notification.persistence.models import NotificationModel
from app.features.post_trade.persistence.models import (
    ExitReviewModel,
    ExitReviewVersionModel,
    PostTradeObservationModel,
)
from app.features.trade_position.persistence.models import PositionModel, TradeModel


@dataclass(frozen=True, slots=True)
class OperationalAction:
    id: str
    source_feature: str
    action_type: str
    priority: str
    state: str
    title: str
    detail: str
    resource_type: str
    resource_id: UUID
    next_action: str
    target: str
    occurred_at: datetime | None


class OperationalWorkspaceReadModel:
    """Project current feature state into deterministic, ephemeral user actions."""

    _PRIORITY_ORDER: ClassVar[dict[str, int]] = {"ACTION": 0, "REVIEW": 1, "BLOCKED": 2}
    _ACTIVE_CANDIDATE_STATUSES = (
        CandidateStatus.IDENTIFIED.value,
        CandidateStatus.UNDER_REVIEW.value,
        CandidateStatus.WATCHING.value,
    )

    def __init__(
        self,
        session: AsyncSession,
        candidate_workflow: RuntimeAwareCandidateLiveWorkflowService | None = None,
    ) -> None:
        self._session = session
        self._candidate_workflow = candidate_workflow or RuntimeAwareCandidateLiveWorkflowService(
            session
        )

    async def list_actions(self, *, workspace_id: UUID) -> tuple[OperationalAction, ...]:
        actions = [
            *(await self._candidate_actions(workspace_id)),
            *(await self._alert_actions(workspace_id)),
            *(await self._notification_failure_actions(workspace_id)),
            *(await self._open_position_actions(workspace_id)),
            *(await self._post_trade_actions(workspace_id)),
        ]
        return tuple(sorted(actions, key=self._sort_key))

    async def _candidate_actions(self, workspace_id: UUID) -> list[OperationalAction]:
        candidates = (
            await self._session.scalars(
                select(CandidateModel)
                .where(
                    CandidateModel.workspace_id == workspace_id,
                    CandidateModel.status.in_(self._ACTIVE_CANDIDATE_STATUSES),
                )
                .order_by(CandidateModel.created_at, CandidateModel.id)
            )
        ).all()

        actions: list[OperationalAction] = []
        for candidate in candidates:
            workflow = await self._candidate_workflow.inspect(
                workspace_id=workspace_id,
                candidate_id=candidate.id,
            )
            if workflow.can_evaluate:
                actions.append(
                    OperationalAction(
                        id=f"candidate:{candidate.id}:evaluation-ready",
                        source_feature="FT-005/FT-020 Candidate",
                        action_type="CANDIDATE_EVALUATION",
                        priority="ACTION",
                        state="ACTIONABLE",
                        title="Kandidat bewerten",
                        detail=(
                            "Alle Voraussetzungen sind erfüllt; die nächste "
                            "Candidate-Evaluation kann gestartet werden."
                        ),
                        resource_type="candidate",
                        resource_id=candidate.id,
                        next_action="Candidate-Evaluation starten",
                        target="/candidates",
                        occurred_at=candidate.created_at,
                    )
                )
                continue

            blocked = next((step for step in workflow.steps if step.status == "BLOCKED"), None)
            if blocked is None:
                continue
            actions.append(
                OperationalAction(
                    id=f"candidate:{candidate.id}:evaluation-blocked:{blocked.code}",
                    source_feature="FT-005/FT-020 Candidate",
                    action_type="CANDIDATE_READINESS",
                    priority="BLOCKED",
                    state="BLOCKED",
                    title="Kandidat vorbereiten",
                    detail=blocked.detail,
                    resource_type="candidate",
                    resource_id=candidate.id,
                    next_action=workflow.next_action or blocked.action or "Voraussetzungen prüfen",
                    target="/candidates",
                    occurred_at=candidate.created_at,
                )
            )
        return actions

    async def _alert_actions(self, workspace_id: UUID) -> list[OperationalAction]:
        alerts = (
            await self._session.scalars(
                select(AlertModel)
                .join(TradeModel, TradeModel.id == AlertModel.trade_id)
                .where(
                    TradeModel.workspace_id == workspace_id,
                    AlertModel.status == AlertStatus.OPEN.value,
                )
                .order_by(AlertModel.detected_at, AlertModel.id)
            )
        ).all()

        return [
            OperationalAction(
                id=f"alert:{alert.id}:open",
                source_feature="Position Monitoring / Alerting",
                action_type="POSITION_ALERT",
                priority="ACTION",
                state="ACTIONABLE",
                title=(
                    "Stop erreicht"
                    if alert.alert_type == AlertType.STOP_REACHED.value
                    else "Target erreicht"
                ),
                detail=alert.reason,
                resource_type="alert",
                resource_id=alert.id,
                next_action="Trade-Management prüfen",
                target=f"/trade-management?trade_id={alert.trade_id}",
                occurred_at=alert.detected_at,
            )
            for alert in alerts
        ]

    async def _notification_failure_actions(self, workspace_id: UUID) -> list[OperationalAction]:
        rows = (
            await self._session.execute(
                select(
                    NotificationModel.id,
                    NotificationModel.channel,
                    NotificationModel.created_at,
                    AlertModel.trade_id,
                )
                .join(AlertModel, AlertModel.id == NotificationModel.alert_id)
                .join(TradeModel, TradeModel.id == AlertModel.trade_id)
                .where(
                    TradeModel.workspace_id == workspace_id,
                    NotificationModel.status == NotificationStatus.FAILED.value,
                )
                .order_by(NotificationModel.created_at, NotificationModel.id)
            )
        ).all()

        return [
            OperationalAction(
                id=f"notification:{notification_id}:failed",
                source_feature="Notification Delivery",
                action_type="NOTIFICATION_DELIVERY_FAILURE",
                priority="ACTION",
                state="ACTIONABLE",
                title="Benachrichtigung fehlgeschlagen",
                detail=(
                    f"Die {channel}-Benachrichtigung zu einem Positions-Alert ist terminal "
                    "fehlgeschlagen."
                ),
                resource_type="notification",
                resource_id=notification_id,
                next_action="Trade-Management prüfen",
                target=f"/trade-management?trade_id={trade_id}",
                occurred_at=created_at,
            )
            for notification_id, channel, created_at, trade_id in rows
        ]

    async def _open_position_actions(self, workspace_id: UUID) -> list[OperationalAction]:
        rows = (
            await self._session.execute(
                select(TradeModel.id, PositionModel.opened_at)
                .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                .where(
                    TradeModel.workspace_id == workspace_id,
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                )
                .order_by(PositionModel.opened_at, TradeModel.id)
            )
        ).all()
        return [
            OperationalAction(
                id=f"trade:{trade_id}:open-position",
                source_feature="FT-009/FT-010 Trade Management",
                action_type="OPEN_POSITION_MANAGEMENT",
                priority="ACTION",
                state="ACTIONABLE",
                title="Offene Position verwalten",
                detail=(
                    "Die Position ist offen. Management, Stop, Targets und bestehende Alerts "
                    "im Trade-Management prüfen."
                ),
                resource_type="trade",
                resource_id=trade_id,
                next_action="Trade-Management öffnen",
                target=f"/trade-management?trade_id={trade_id}",
                occurred_at=opened_at,
            )
            for trade_id, opened_at in rows
        ]

    async def _post_trade_actions(self, workspace_id: UUID) -> list[OperationalAction]:
        closed = (
            await self._session.execute(
                select(TradeModel.id, PositionModel.closed_at)
                .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                .where(
                    TradeModel.workspace_id == workspace_id,
                    PositionModel.open_quantity == 0,
                    PositionModel.closed_at.is_not(None),
                )
                .order_by(PositionModel.closed_at, TradeModel.id)
            )
        ).all()

        actions: list[OperationalAction] = []
        for trade_id, closed_at in closed:
            observation = await self._session.scalar(
                select(PostTradeObservationModel).where(
                    PostTradeObservationModel.workspace_id == workspace_id,
                    PostTradeObservationModel.trade_id == trade_id,
                )
            )
            if observation is None:
                actions.append(
                    self._review_action(
                        trade_id=trade_id,
                        suffix="observation",
                        action_type="POST_TRADE_OBSERVATION",
                        title="Nachbeobachtung starten",
                        detail=(
                            "Der Trade ist geschlossen und hat noch keine "
                            "FT-011-Nachbeobachtung."
                        ),
                        next_action="Nachbeobachtung öffnen",
                        occurred_at=closed_at,
                    )
                )
                continue
            if observation.status == "ACTIVE":
                continue

            review = await self._session.scalar(
                select(ExitReviewModel).where(
                    ExitReviewModel.workspace_id == workspace_id,
                    ExitReviewModel.post_trade_observation_id == observation.id,
                )
            )
            if review is None:
                actions.append(
                    self._review_action(
                        trade_id=trade_id,
                        suffix="exit-review-create",
                        action_type="EXIT_REVIEW",
                        title="Exit Review erstellen",
                        detail=(
                            "Die Nachbeobachtung ist abgeschlossen; ein Exit Review ist noch "
                            "nicht angelegt."
                        ),
                        next_action="Exit Review öffnen",
                        occurred_at=observation.completed_at or closed_at,
                    )
                )
                continue

            current = await self._session.scalar(
                select(ExitReviewVersionModel)
                .where(
                    ExitReviewVersionModel.exit_review_id == review.id,
                    ExitReviewVersionModel.currentness == "CURRENT",
                )
                .order_by(ExitReviewVersionModel.version.desc())
                .limit(1)
            )
            if current is not None and current.status == "FINALIZED":
                continue

            if current is not None and current.status == "DRAFT":
                title = "Exit Review abschließen"
                detail = (
                    "Für den abgeschlossenen Trade ist ein aktueller Exit-Review-Entwurf offen."
                )
                suffix = "exit-review-draft"
            else:
                title = "Exit Review aktualisieren"
                detail = (
                    "Die Nachbeobachtung ist abgeschlossen, aber es gibt kein aktuelles "
                    "finalisiertes Exit Review."
                )
                suffix = "exit-review-refresh"
            actions.append(
                self._review_action(
                    trade_id=trade_id,
                    suffix=suffix,
                    action_type="EXIT_REVIEW",
                    title=title,
                    detail=detail,
                    next_action="Exit Review öffnen",
                    occurred_at=observation.completed_at or closed_at,
                )
            )
        return actions

    @staticmethod
    def _review_action(
        *,
        trade_id: UUID,
        suffix: str,
        action_type: str,
        title: str,
        detail: str,
        next_action: str,
        occurred_at: datetime | None,
    ) -> OperationalAction:
        return OperationalAction(
            id=f"trade:{trade_id}:{suffix}",
            source_feature="FT-011 Post Trade",
            action_type=action_type,
            priority="REVIEW",
            state="ACTIONABLE",
            title=title,
            detail=detail,
            resource_type="trade",
            resource_id=trade_id,
            next_action=next_action,
            target=f"/post-trade?trade_id={trade_id}",
            occurred_at=occurred_at,
        )

    def _sort_key(self, action: OperationalAction) -> tuple[int, datetime, str]:
        occurred_at = action.occurred_at
        if occurred_at is None:
            occurred_at = datetime.max.replace(tzinfo=UTC)
        elif occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        return (self._PRIORITY_ORDER[action.priority], occurred_at, action.id)
