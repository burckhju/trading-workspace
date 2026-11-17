"""Atomic B04/B57 evaluation on owner snapshots, with one alert per loss episode."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import aliased
from sqlalchemy.pool import NullPool

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.market_data.domain.status_observations import StatusRouteBinding
from app.features.market_data.service.status_observations import MarketStatusReader
from app.features.notification.domain.models import NotificationChannel
from app.features.notification.persistence.repositories import SqlAlchemyNotificationRepository
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_b04_notifications,
)
from app.features.position_monitoring.domain.hebeltrader_loss import (
    BASELINE_ID,
    BASELINE_VERSION,
    RULE_KEY,
    RULE_SCOPE,
    RULE_VERSION,
    LossDecision,
    decide_loss,
)
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossEpisodeModel as Episode,
)
from app.features.position_monitoring.service.hebeltrader_b58_sources import B58SourceRegistry
from app.features.position_monitoring.service.hebeltrader_loss_inputs import (
    JSON_VALUE,
    LossInputs,
    read_loss_inputs,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyTradeRepository


async def latest_assessment(
    session: AsyncSession,
    workspace_id: UUID,
    position_id: UUID,
) -> Assessment | None:
    successor = aliased(Assessment)
    row: Assessment | None = await session.scalar(
        select(Assessment).where(
            Assessment.workspace_id == workspace_id,
            Assessment.position_id == position_id,
            Assessment.rule_version == RULE_VERSION,
            ~exists().where(successor.previous_assessment_id == Assessment.id),
        )
    )
    return row


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _stable_material(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _stable_material(item)
            for key, item in value.items()
            if key
            not in {
                "read_at",
                "known_at",
                "read_started_at",
                "read_completed_at",
                "evaluated_at",
                "age_seconds",
            }
        }
    if isinstance(value, (tuple, list)):
        return [_stable_material(item) for item in value]
    return value


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)


@asynccontextmanager
async def _owner_snapshot(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Read after the trade lock without borrowing its pool's last connection.

    One short-lived connection is bounded by each evaluator that already owns
    a trade lock. This also works with an application pool of size one. The
    existing database URL carries the same database, credentials and options;
    neither connection nor credentials are retained beyond this command.
    """
    snapshot_engine = create_async_engine(engine.url, poolclass=NullPool)
    try:
        async with AsyncSession(
            snapshot_engine, expire_on_commit=False, autoflush=False
        ) as snapshot:
            try:
                await snapshot.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await snapshot.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                yield snapshot
            finally:
                await snapshot.rollback()
    finally:
        await snapshot_engine.dispose()


@dataclass(frozen=True, slots=True)
class LossEvaluationResult:
    assessment_id: UUID
    outcome: str
    reasons: tuple[str, ...]
    episode_id: UUID | None
    episode_active: bool
    unchanged: bool
    alert_created: bool
    notification_created: bool


class HebeltraderLossService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        sources: B58SourceRegistry | None = None,
    ) -> None:
        self._session = session
        self._sources = sources or B58SourceRegistry()

    async def evaluate(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        position_id: UUID,
        notifications_enabled: bool = False,
        now: datetime | None = None,
    ) -> LossEvaluationResult:
        """Command only. The existing trade lock serializes evaluations and corrections.

        Start the consistent read snapshot *after* obtaining the owner lock, as
        for target assessments. Append-only inputs do not update the trade row;
        a repeatable-read snapshot taken before waiting would otherwise be old.
        """
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await self._session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            if await SqlAlchemyTradeRepository(self._session).get(workspace_id, trade_id) is None:
                raise LookupError("B04_TRADE_NOT_FOUND")
            engine = self._session.bind
            if not isinstance(engine, AsyncEngine):
                raise RuntimeError("B04 evaluation requires an engine-backed session")
            evaluated_at = now or datetime.now(UTC)
            if evaluated_at.utcoffset() is None:
                raise ValueError("B04 evaluation requires an aware clock")
            evaluated_at = evaluated_at.astimezone(UTC)
            async with _owner_snapshot(engine) as snapshot:
                inputs = await read_loss_inputs(
                    snapshot,
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    position_id=position_id,
                    now=evaluated_at,
                )
                route, saved = inputs.saved.route, inputs.saved
                status = None
                if route is not None and saved.provider is not None:
                    isin = inputs.material["warrant_isin"]
                    if isin:
                        status = await MarketStatusReader(snapshot).read(
                            route=StatusRouteBinding(
                                workspace_id,
                                inputs.product_id,
                                route.warrant_listing_id,
                                saved.provider,
                                route.identity_key,
                                isin,
                                route.venue_mic,
                            ),
                            event_at=evaluated_at,
                            known_at=evaluated_at,
                        )
                source = self._sources.qualify(saved, status)
                inputs.material["status_observations"] = (
                    JSON_VALUE.dump_python(asdict(status), mode="json") if status else None
                )
                inputs.material["source_qualification"] = asdict(source)
                previous = await latest_assessment(snapshot, workspace_id, position_id)
                latest_qualified = await snapshot.scalar(
                    select(Assessment)
                    .where(
                        Assessment.workspace_id == workspace_id,
                        Assessment.position_id == position_id,
                        Assessment.rule_version == RULE_VERSION,
                        Assessment.outcome.in_(("LOSS", "RECOVERED")),
                    )
                    .order_by(Assessment.bid_at.desc(), Assessment.recorded_at.desc())
                    .limit(1)
                )
                decision = self._decision(inputs, source.reasons, latest_qualified)
                fingerprint = self._input_fingerprint(inputs, decision)
                # Snapshot objects remain scalar facts; all commands use the
                # locked outer transaction and preserve historical input JSON.
                previous_id = previous.id if previous else None
                duplicate = previous is not None and previous.input_fingerprint == fingerprint
            return await self._persist(
                inputs,
                decision,
                fingerprint,
                previous_id,
                duplicate,
                evaluated_at,
                notifications_enabled,
            )
        except Exception:
            await self._session.rollback()
            raise

    @staticmethod
    def _decision(
        inputs: LossInputs,
        source_problems: tuple[str, ...],
        latest_qualified: Assessment | None,
    ) -> LossDecision:
        material = inputs.material
        bid = material["bid"]
        count = material["underlying_sessions"]["count"]
        position = material["economic_basis"]["position"]
        bid_at = datetime.fromisoformat(bid["original_bid_at"]) if bid["original_bid_at"] else None
        problems = (*inputs.problems, *source_problems)
        if latest_qualified is not None and bid_at is not None and latest_qualified.bid_at:
            old_at = _utc(latest_qualified.bid_at)
            if bid_at < old_at:
                problems += ("B04_OUT_OF_ORDER_BID",)
            elif (
                bid_at == old_at
                and bid["price"] is not None
                and Decimal(bid["price"]) != Decimal(latest_qualified.inputs["bid"]["price"])
            ):
                problems += ("B04_CONFLICTING_BID_AT_SAME_TIME",)
        return decide_loss(
            closed=inputs.closed,
            bid=Decimal(bid["price"]) if bid["price"] is not None else None,
            gross_entry=Decimal(position["average_entry_price"]),
            bid_at=bid_at,
            remaining_quantity=position["open_quantity"],
            completed_sessions_at_bid=count["completed_sessions"] if count else None,
            input_problems=problems,
        )

    @staticmethod
    def _input_fingerprint(inputs: LossInputs, decision: LossDecision) -> str:
        material = inputs.material
        status = material["status_observations"]
        scale = material["product_scale"]
        # No reading clock or growing age enters the identity. A fresh/stale,
        # calendar, source, correction or status transition still changes it.
        return _fingerprint(
            _stable_material(
                {
                    "rule": RULE_KEY,
                    "owner": inputs.owner_basis_id,
                    "quote": material["saved_quote"].get("provenance", {}),
                    "route": material["saved_quote"]["route"],
                    "bid": (decision.bid, decision.bid_at),
                    "source": material["source_qualification"],
                    "status_facts": (
                        [item["fingerprint"] for item in status["latest_observations"]]
                        + [
                            (
                                status["latest_capture"]["fingerprint"]
                                if status["latest_capture"]
                                else None
                            )
                        ]
                        + [item["fingerprint"] for item in status["point_observations"]]
                        if status
                        else None
                    ),
                    "scale": scale,
                    "product_calendar": material["product_sessions"]["calendar"],
                    "underlying_calendar": material["underlying_sessions"]["calendar"],
                    "underlying_period": material["underlying_sessions"]["period"]["fingerprint"],
                    "outcome": decision.outcome,
                    "reasons": decision.reasons,
                }
            )
        )

    async def _persist(
        self,
        inputs: LossInputs,
        decision: LossDecision,
        fingerprint: str,
        previous_id: UUID | None,
        duplicate: bool,
        now: datetime,
        notifications_enabled: bool,
    ) -> LossEvaluationResult:
        session = self._session
        active = await session.scalar(
            select(Episode).where(
                Episode.workspace_id == inputs.workspace_id,
                Episode.position_id == inputs.position_id,
                Episode.rule_version == RULE_VERSION,
                Episode.closed_at.is_(None),
            )
        )
        alert_created = False
        assessment_id = previous_id if duplicate else uuid4()
        assert assessment_id is not None
        if not duplicate:
            session.add(
                Assessment(
                    id=assessment_id,
                    workspace_id=inputs.workspace_id,
                    trade_id=inputs.trade_id,
                    position_id=inputs.position_id,
                    rule_version=RULE_VERSION,
                    previous_assessment_id=previous_id,
                    input_fingerprint=fingerprint,
                    owner_basis_id=inputs.owner_basis_id,
                    outcome=decision.outcome,
                    evaluated_at=now,
                    recorded_at=datetime.now(UTC),
                    bid_at=decision.bid_at,
                    inputs=inputs.material,
                    result=JSON_VALUE.dump_python(asdict(decision), mode="json"),
                )
            )
            await session.flush()
        alerts = SqlAlchemyAlertRepository(session)
        if decision.outcome == "LOSS" and active is None:
            sequence = (
                int(
                    await session.scalar(
                        select(func.max(Episode.episode_number)).where(
                            Episode.workspace_id == inputs.workspace_id,
                            Episode.position_id == inputs.position_id,
                            Episode.rule_version == RULE_VERSION,
                        )
                    )
                    or 0
                )
                + 1
            )
            episode_id = uuid4()
            assert decision.bid is not None
            alert = Alert(
                id=uuid4(),
                position_id=inputs.position_id,
                trade_id=inputs.trade_id,
                alert_type=AlertType.HEBELTRADER_B04_LOSS,
                severity=AlertSeverity.WARNING,
                rule_key=RULE_KEY,
                reason="Original-Geldkurs unter persönlichem Bruttoeinstand nach mindestens "
                "20 abgeschlossenen Basiswertsitzungen. Vollständigen Restausstieg prüfen.",
                observed_value=decision.bid,
                threshold_value=decision.gross_entry,
                market_data_observed_at=decision.bid_at,
                detected_at=now,
                price_context={
                    "basis": "WARRANT",
                    "price_type": "BID",
                    "currency": inputs.material["economic_basis"]["cost_basis_currency"],
                    "provider": inputs.saved.provider,
                    "observed_at": decision.bid_at.isoformat() if decision.bid_at else None,
                    "rule_version": RULE_VERSION,
                    "rule_scope": RULE_SCOPE,
                    "baseline_id": BASELINE_ID,
                    "baseline_version": BASELINE_VERSION,
                    "remaining_quantity": str(decision.remaining_quantity),
                    "completed_sessions_at_bid": str(decision.completed_sessions_at_bid),
                    "episode_id": str(episode_id),
                    "assessment_id": str(assessment_id),
                    "owner_basis_id": inputs.owner_basis_id,
                    "source_qualification": inputs.material["source_qualification"][
                        "qualification_reference"
                    ],
                },
            )
            await alerts.add(alert)
            await session.flush()
            active = Episode(
                id=episode_id,
                workspace_id=inputs.workspace_id,
                trade_id=inputs.trade_id,
                position_id=inputs.position_id,
                rule_version=RULE_VERSION,
                episode_number=sequence,
                opening_assessment_id=assessment_id,
                alert_id=alert.id,
                opened_at=now,
            )
            session.add(active)
            alert_created = True
        elif active is not None and decision.outcome in {"RECOVERED", "CLOSED"}:
            active.closed_at = now
            active.closing_assessment_id = assessment_id
            active.close_reason = decision.reasons[0]
            await alerts.resolve(active.alert_id, resolved_at=now)
            await suppress_pending_b04_notifications(
                session,
                alert_id=active.alert_id,
                now=now,
                reason=(
                    "B04_POSITION_CLOSED" if decision.outcome == "CLOSED" else "B04_ALERT_RESOLVED"
                ),
            )
        notification_created = False
        if active is not None and active.closed_at is None and notifications_enabled:
            notification_created = await self._ensure_notification(active, inputs, now)
        await session.commit()
        return LossEvaluationResult(
            assessment_id,
            decision.outcome,
            decision.reasons,
            active.id if active else None,
            active is not None and active.closed_at is None,
            duplicate,
            alert_created,
            notification_created,
        )

    async def _ensure_notification(
        self, episode: Episode, inputs: LossInputs, now: datetime
    ) -> bool:
        repository = SqlAlchemyNotificationRepository(self._session)
        existing = await repository.get_for_alert(
            alert_id=episode.alert_id,
            channel=NotificationChannel.TELEGRAM,
            destination_key="telegram_default",
        )
        if existing is not None:
            return False
        alert = await SqlAlchemyAlertRepository(self._session).get(episode.alert_id)
        assert alert is not None
        service = AlertNotificationService(notifications=repository, new_id=uuid4, now=lambda: now)
        await service.create_telegram(
            alert=alert,
            symbol=inputs.material["warrant_isin"] or "Optionsschein",
            warrant_name=inputs.material["warrant_name"],
            warrant_isin=inputs.material["warrant_isin"],
            warrant_wkn=inputs.material["warrant_wkn"],
        )
        return True
