"""Atomic Product/calendar deadline assessments and deduplicated review notices."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import aliased

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.notification.domain.models import NotificationChannel
from app.features.notification.persistence.repositories import SqlAlchemyNotificationRepository
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_review_notifications,
)
from app.features.position_monitoring.domain.product_deadline_review import (
    EPISODE_KINDS,
    RULE_KEY,
    RULE_SCOPE,
    RULE_VERSION,
    DeadlineEpisodeKind,
    ProductDeadlineDecision,
    decide_product_deadline_review,
    desired_deadline_episode,
)
from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineEpisodeModel as Episode,
)
from app.features.position_monitoring.service.hebeltrader_loss import (
    _fingerprint,
    _owner_snapshot,
    _stable_material,
    _utc,
)
from app.features.position_monitoring.service.product_deadline_review_inputs import (
    JSON_VALUE,
    ProductDeadlineInputs,
    read_product_deadline_inputs,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyTradeRepository


async def latest_product_deadline_assessment(
    session: AsyncSession, workspace_id: UUID, position_id: UUID
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


def product_deadline_event_key(
    inputs: ProductDeadlineInputs, decision: ProductDeadlineDecision
) -> str | None:
    """Business-event identity survives rereads and unchanged source revisions."""
    calculation = decision.calculation
    if decision.reminder_due is not True or calculation is None:
        return None
    evidence = inputs.material["product_evidence"]
    return _fingerprint(
        {
            "warrant_id": inputs.warrant_id,
            "exit_listing_id": evidence["exit_listing_id"],
            "relevant_product_date": calculation.relevant_product_date,
            "exit_session_date": calculation.exit_session_date,
            "stage": decision.outcome,
            "scheduled_at": decision.scheduled_at,
            "scheduled_on": decision.scheduled_on,
        }
    )


def product_deadline_input_fingerprint(
    inputs: ProductDeadlineInputs, decision: ProductDeadlineDecision
) -> str:
    # Audit actual owner corrections and source revisions independently from
    # the identity of a logical reminder. Advancing read clocks alone is not an
    # input change; crossing a documented stage boundary is.
    return _fingerprint(
        _stable_material(
            {
                "rule": RULE_KEY,
                "owner": inputs.owner_basis_id,
                "inputs": inputs.material,
                "decision": asdict(decision),
                "event_key": product_deadline_event_key(inputs, decision),
            }
        )
    )


@dataclass(frozen=True, slots=True)
class ProductDeadlineEvaluationResult:
    assessment_id: UUID
    outcome: str
    reasons: tuple[str, ...]
    unchanged: bool
    alerts_created: int
    notifications_created: int
    data_problem_active: bool
    reminder_active: bool


class ProductDeadlineReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        position_id: UUID,
        notifications_enabled: bool = False,
        now: datetime | None = None,
    ) -> ProductDeadlineEvaluationResult:
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await self._session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            if await SqlAlchemyTradeRepository(self._session).get(workspace_id, trade_id) is None:
                raise LookupError("PRODUCT_DEADLINE_TRADE_NOT_FOUND")
            engine = self._session.bind
            if not isinstance(engine, AsyncEngine):
                raise RuntimeError("Product deadline review requires an engine-backed session")
            evaluated_at = now or datetime.now(UTC)
            if evaluated_at.utcoffset() is None:
                raise ValueError("Product deadline review requires an aware clock")
            evaluated_at = evaluated_at.astimezone(UTC)
            # The existing economic-owner lock serializes SELL/corrections and
            # parallel evaluations. Its read snapshot opens after that lock and
            # uses the established pool-size-one-safe helper.
            async with _owner_snapshot(engine) as snapshot:
                inputs = await read_product_deadline_inputs(
                    snapshot,
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    position_id=position_id,
                    now=evaluated_at,
                )
                previous = await latest_product_deadline_assessment(
                    snapshot, workspace_id, position_id
                )
                if previous is not None and evaluated_at < _utc(previous.evaluated_at):
                    raise ValueError("PRODUCT_DEADLINE_EVALUATION_CLOCK_MOVED_BACKWARDS")
                decision = decide_product_deadline_review(
                    closed=inputs.closed,
                    calculation=inputs.calculation,
                    input_problems=inputs.problems,
                )
                fingerprint = product_deadline_input_fingerprint(inputs, decision)
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

    async def _persist(
        self,
        inputs: ProductDeadlineInputs,
        decision: ProductDeadlineDecision,
        fingerprint: str,
        previous_id: UUID | None,
        duplicate: bool,
        now: datetime,
        notifications_enabled: bool,
    ) -> ProductDeadlineEvaluationResult:
        session = self._session
        active = {
            row.kind: row
            for row in await session.scalars(
                select(Episode).where(
                    Episode.workspace_id == inputs.workspace_id,
                    Episode.position_id == inputs.position_id,
                    Episode.rule_version == RULE_VERSION,
                    Episode.closed_at.is_(None),
                )
            )
        }
        assessment_id = previous_id if duplicate else uuid4()
        assert assessment_id is not None
        event_key = product_deadline_event_key(inputs, decision)
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
                    inputs=inputs.material,
                    result=JSON_VALUE.dump_python(
                        {**asdict(decision), "deadline_event_key": event_key}, mode="json"
                    ),
                )
            )
            await session.flush()
        alerts_created = notifications_created = 0
        for kind in EPISODE_KINDS:
            episode = active.get(kind)
            desired = desired_deadline_episode(kind, decision)
            changed_event = (
                kind == "DEADLINE_REVIEW"
                and desired is True
                and episode is not None
                and episode.event_key != event_key
            )
            if episode is not None and (desired is False or changed_event):
                episode.closed_at = now
                episode.closing_assessment_id = assessment_id
                episode.close_reason = (
                    "POSITION_CLOSED_OR_CANCELLED"
                    if decision.outcome == "CLOSED"
                    else (
                        "PRODUCT_DEADLINE_STAGE_OR_PREMISE_CHANGED"
                        if kind == "DEADLINE_REVIEW"
                        else "PRODUCT_DEADLINE_INPUTS_AVAILABLE"
                    )
                )
                await SqlAlchemyAlertRepository(session).resolve(episode.alert_id, resolved_at=now)
                await suppress_pending_review_notifications(
                    session,
                    alert_id=episode.alert_id,
                    now=now,
                    reason=(
                        "REVIEW_POSITION_CLOSED"
                        if decision.outcome == "CLOSED"
                        else "REVIEW_ALERT_RESOLVED"
                    ),
                )
                active.pop(kind)
                episode = None
            if desired is True and episode is None:
                prior_event = (
                    await session.scalar(
                        select(Episode).where(
                            Episode.workspace_id == inputs.workspace_id,
                            Episode.position_id == inputs.position_id,
                            Episode.rule_version == RULE_VERSION,
                            Episode.kind == "DEADLINE_REVIEW",
                            Episode.event_key == event_key,
                        )
                    )
                    if kind == "DEADLINE_REVIEW"
                    else None
                )
                if prior_event is None:
                    episode = await self._open_episode(kind, inputs, decision, assessment_id, now)
                    active[kind] = episode
                    alerts_created += 1
            # A preserved old reminder during a data gap cannot acquire a new
            # outbox item. Existing pending items additionally recheck owners
            # through the delivery hook before sending.
            if (
                desired is True
                and episode is not None
                and episode.closed_at is None
                and notifications_enabled
            ):
                notifications_created += int(await self._ensure_notification(episode, inputs, now))
        await session.commit()
        return ProductDeadlineEvaluationResult(
            assessment_id,
            decision.outcome,
            decision.reasons,
            duplicate,
            alerts_created,
            notifications_created,
            "DATA_UNAVAILABLE" in active,
            "DEADLINE_REVIEW" in active,
        )

    async def _open_episode(
        self,
        kind: DeadlineEpisodeKind,
        inputs: ProductDeadlineInputs,
        decision: ProductDeadlineDecision,
        assessment_id: UUID,
        now: datetime,
    ) -> Episode:
        sequence = (
            int(
                await self._session.scalar(
                    select(func.max(Episode.episode_number)).where(
                        Episode.workspace_id == inputs.workspace_id,
                        Episode.position_id == inputs.position_id,
                        Episode.rule_version == RULE_VERSION,
                        Episode.kind == kind,
                    )
                )
                or 0
            )
            + 1
        )
        episode_id = uuid4()
        reasons = {
            "WARNING_DUE": (
                "Die Sitzung vor dem aus dokumentierten Produktterminen berechneten "
                "Prüftag hat begonnen. Position prüfen; die produktspezifische "
                "Ausführungsfrist ist nicht verifiziert."
            ),
            "EXIT_SESSION_STARTED": (
                "Der aus dokumentierten Produktterminen berechnete Prüftag hat begonnen. "
                "Position prüfen; die produktspezifische Ausführungsfrist ist nicht verifiziert."
            ),
            "CALENDAR_SESSION_ENDED": (
                "Die dokumentierte Kalendersitzung des berechneten Prüftags ist beendet. "
                "Position prüfen; dies belegt keine produktspezifische B20-Ausführungsfrist."
            ),
            "WARNING_DAY_REACHED": (
                "Der dokumentierte Börsentag vor dem berechneten Produkt-Prüftag ist erreicht. "
                "Position prüfen; Produktzeiten und Ausführungsfrist sind nicht verifiziert."
            ),
            "DEADLINE_DAY_REACHED": (
                "Der aus dokumentierten Börsentagen berechnete Produkt-Prüftag ist erreicht. "
                "Position prüfen; dies belegt weder Handelsbeginn noch B20-Ausführungsfrist."
            ),
            "DEADLINE_DAY_PASSED": (
                "Das lokale Datum des berechneten Produkt-Prüftags ist vergangen. "
                "Position prüfen; konkrete Produktzeiten und B20-Ausführungsfrist fehlen."
            ),
        }
        reason = (
            "Die Produktterminüberwachung ist wegen fehlender oder ungeeigneter Belege "
            "nicht beurteilbar. Ein früherer Terminhinweis bleibt davon getrennt sichtbar."
            if kind == "DATA_UNAVAILABLE"
            else reasons[decision.outcome]
        )
        alert = Alert(
            id=uuid4(),
            position_id=inputs.position_id,
            trade_id=inputs.trade_id,
            alert_type=(
                AlertType.POSITION_DATA_UNAVAILABLE
                if kind == "DATA_UNAVAILABLE"
                else AlertType.PRODUCT_DEADLINE_REVIEW
            ),
            severity=AlertSeverity.WARNING,
            rule_key=f"{RULE_KEY}:{kind}",
            reason=reason,
            observed_value=None,
            threshold_value=None,
            market_data_observed_at=None,
            detected_at=now,
            price_context=product_deadline_context(
                inputs, decision, kind, assessment_id, episode_id, now
            ),
        )
        await SqlAlchemyAlertRepository(self._session).add(alert)
        await self._session.flush()
        episode = Episode(
            id=episode_id,
            workspace_id=inputs.workspace_id,
            trade_id=inputs.trade_id,
            position_id=inputs.position_id,
            rule_version=RULE_VERSION,
            kind=kind,
            event_key=product_deadline_event_key(inputs, decision),
            episode_number=sequence,
            opening_assessment_id=assessment_id,
            alert_id=alert.id,
            opened_at=now,
        )
        self._session.add(episode)
        return episode

    async def _ensure_notification(
        self, episode: Episode, inputs: ProductDeadlineInputs, now: datetime
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
        await AlertNotificationService(
            notifications=repository, new_id=uuid4, now=lambda: now
        ).create_telegram(
            alert=alert,
            symbol=inputs.material["warrant_isin"] or "Optionsschein",
            warrant_name=inputs.material["warrant_name"],
            warrant_isin=inputs.material["warrant_isin"],
            warrant_wkn=inputs.material["warrant_wkn"],
        )
        return True


def product_deadline_context(
    inputs: ProductDeadlineInputs,
    decision: ProductDeadlineDecision,
    kind: DeadlineEpisodeKind,
    assessment_id: UUID,
    episode_id: UUID,
    now: datetime,
) -> dict[str, str | None]:
    evidence = inputs.material.get("product_evidence") or {}
    calculation = decision.calculation
    dates = (
        JSON_VALUE.dump_python(asdict(calculation), mode="json") if calculation is not None else {}
    )
    return {
        "scope": RULE_SCOPE,
        "rule_version": RULE_VERSION,
        "qualified_b05": "false",
        "product_cutoff_status": "UNVERIFIED",
        "decision_kind": "POSITION_REVIEW",
        "execution_usable": "false",
        "deadline_stage": calculation.stage if calculation else None,
        "relevant_product_date": dates.get("relevant_product_date"),
        "maturity_on": evidence.get("maturity_on"),
        "last_trading_on": evidence.get("last_trading_on"),
        "exit_listing_id": evidence.get("exit_listing_id"),
        "exit_venue_mic": evidence.get("exit_venue_mic"),
        "exit_session_date": dates.get("exit_session_date"),
        "exit_session_opens_at": dates.get("exit_session_opens_at"),
        "warning_at": dates.get("warning_at"),
        "calendar_session_closes_at": dates.get("calendar_session_closes_at"),
        "calendar_revision_id": dates.get("calendar_revision_id"),
        "calendar_verification": dates.get("calendar_verification"),
        "calendar_precision": (
            dates.get("calendar_precision", "ORIGINAL_SESSION_TIMES") if calculation else None
        ),
        "calendar_calculation_scope": dates.get("scope"),
        "calendar_timezone": dates.get("calendar_timezone"),
        "warning_session_date": dates.get("warning_session_date"),
        "product_evidence_revision_id": evidence.get("revision_id"),
        "product_verification": evidence.get("verification"),
        "source_reference": evidence.get("source_reference"),
        "scheduled_at": decision.scheduled_at.isoformat() if decision.scheduled_at else None,
        "scheduled_on": decision.scheduled_on.isoformat() if decision.scheduled_on else None,
        "detected_at": now.isoformat(),
        "deadline_event_key": product_deadline_event_key(inputs, decision),
        "episode_kind": kind,
        "episode_id": str(episode_id),
        "assessment_id": str(assessment_id),
        "owner_basis_id": inputs.owner_basis_id,
        "data_problem_reasons": ",".join(decision.reasons) if kind == "DATA_UNAVAILABLE" else None,
        "isin": inputs.material["warrant_isin"],
    }
