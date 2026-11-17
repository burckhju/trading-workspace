"""Atomic, separately versioned review assessments and three durable notice types."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import aliased

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.notification.domain.models import NotificationChannel
from app.features.notification.persistence.repositories import (
    SqlAlchemyNotificationRepository,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_review_notifications,
)
from app.features.position_monitoring.domain.indicative_entry import (
    EPISODE_KINDS,
    RULE_KEY,
    RULE_SCOPE,
    RULE_VERSION,
    EpisodeKind,
    IndicativeDecision,
    decide_indicative_entry,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryEpisodeModel as Episode,
)
from app.features.position_monitoring.service.hebeltrader_loss import (
    _fingerprint,
    _owner_snapshot,
    _stable_material,
    _utc,
)
from app.features.position_monitoring.service.indicative_entry_inputs import (
    JSON_VALUE,
    IndicativeInputs,
    read_indicative_inputs,
    status_point_context,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeRepository,
)


async def latest_indicative_assessment(
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


@dataclass(frozen=True, slots=True)
class IndicativeEvaluationResult:
    assessment_id: UUID
    outcome: str
    reasons: tuple[str, ...]
    unchanged: bool
    alerts_created: int
    notifications_created: int
    data_problem_active: bool
    review_due: bool
    loss_episode_active: bool


class IndicativeEntryService:
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
        refresh_failed: bool = False,
    ) -> IndicativeEvaluationResult:
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await self._session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            if await SqlAlchemyTradeRepository(self._session).get(workspace_id, trade_id) is None:
                raise LookupError("REVIEW_TRADE_NOT_FOUND")
            engine = self._session.bind
            if not isinstance(engine, AsyncEngine):
                raise RuntimeError("Indicative review requires an engine-backed session")
            evaluated_at = now or datetime.now(UTC)
            if evaluated_at.utcoffset() is None:
                raise ValueError("Indicative review requires an aware clock")
            evaluated_at = evaluated_at.astimezone(UTC)
            # Reuse only the technical snapshot helper, not B04 inputs or state.
            # It opens after the trade lock and works with pool_size=1/overflow=0.
            async with _owner_snapshot(engine) as snapshot:
                inputs = await read_indicative_inputs(
                    snapshot,
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    position_id=position_id,
                    now=evaluated_at,
                )
                previous = await latest_indicative_assessment(snapshot, workspace_id, position_id)
                inputs = self._preserve_refresh_failure(inputs, previous, refresh_failed)
                latest_price = await snapshot.scalar(
                    select(Assessment)
                    .where(
                        Assessment.workspace_id == workspace_id,
                        Assessment.position_id == position_id,
                        Assessment.rule_version == RULE_VERSION,
                        Assessment.outcome.in_(("BELOW_ENTRY", "AT_OR_ABOVE_ENTRY")),
                        Assessment.result["evaluation_mode"].as_string()
                        == inputs.quote.evaluation_mode,
                        Assessment.inputs["saved_quote"]["provider"].as_string()
                        == inputs.saved.provider,
                        Assessment.inputs["saved_quote"]["route"]["identity_key"].as_string()
                        == (inputs.saved.route.identity_key if inputs.saved.route else None),
                    )
                    .order_by(Assessment.ordering_at.desc(), Assessment.recorded_at.desc())
                    .limit(1)
                )
                if previous is not None and evaluated_at < _utc(previous.evaluated_at):
                    raise ValueError("REVIEW_EVALUATION_CLOCK_MOVED_BACKWARDS")
                decision = self._decision(inputs, latest_price)
                fingerprint = self._input_fingerprint(inputs, decision)
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
    def _preserve_refresh_failure(
        inputs: IndicativeInputs, previous: Assessment | None, failed: bool
    ) -> IndicativeInputs:
        """Restart is not evidence that a failed acquisition succeeded later.

        A transient acquisition error may occur before the retained owner can
        append a status gap. Keep that actual failed attempt while precisely
        the same selected last-success remains; a new successful receipt or a
        separately bound source is assessed on its own facts.
        """
        if inputs.closed:
            return inputs

        def identity(material: dict[str, object]) -> object:
            saved = material.get("saved_quote")
            if not isinstance(saved, dict):
                return None
            return (
                saved.get("provider"),
                saved.get("identity_key"),
                saved.get("retrieved_at"),
            )

        preserved = (
            previous is not None
            and previous.inputs.get("current_refresh_failed") is True
            and identity(previous.inputs) == identity(inputs.material)
        )
        if failed or preserved:
            return replace(
                inputs,
                problems=(*inputs.problems, "REVIEW_QUOTE_REFRESH_FAILED"),
                material={**inputs.material, "current_refresh_failed": True},
            )
        return inputs

    @staticmethod
    def _decision(
        inputs: IndicativeInputs,
        latest_price: Assessment | None,
    ) -> IndicativeDecision:
        problems = list(inputs.problems)
        quote = inputs.quote
        same_stream = (
            latest_price is not None
            and latest_price.result.get("evaluation_mode") == quote.evaluation_mode
            and latest_price.inputs.get("saved_quote", {}).get("provider") == inputs.saved.provider
            and latest_price.inputs.get("saved_quote", {}).get("route", {}).get("identity_key")
            == (inputs.saved.route.identity_key if inputs.saved.route else None)
        )
        if (
            same_stream
            and latest_price is not None
            and quote.ordering_at is not None
            and latest_price.ordering_at
        ):
            previous_at = _utc(latest_price.ordering_at)
            if quote.ordering_at < previous_at:
                problems.append("REVIEW_OUT_OF_ORDER_OBSERVATION")
            elif (
                quote.ordering_at == previous_at
                and quote.bid is not None
                and Decimal(latest_price.result["bid"]) != quote.bid
            ):
                problems.append("REVIEW_CONFLICTING_PRICE_AT_SAME_TIME")
        position = inputs.material["economic_basis"]["position"]
        return decide_indicative_entry(
            closed=inputs.closed,
            gross_entry=Decimal(position["average_entry_price"]),
            remaining_quantity=position["open_quantity"],
            quote=quote,
            review_completed_sessions=(
                inputs.review_count.completed_sessions if inputs.review_count else None
            ),
            completed_sessions=(
                inputs.comparison_count.completed_sessions if inputs.comparison_count else None
            ),
            input_problems=tuple(problems),
        )

    @staticmethod
    def _input_fingerprint(inputs: IndicativeInputs, decision: IndicativeDecision) -> str:
        material = inputs.material
        route = asdict(inputs.saved.route) if inputs.saved.route else None
        status = material.get("status_observations") or {}
        observations = list(status.get("latest_observations", ()))
        if status.get("latest_capture") is not None:
            observations.append(status["latest_capture"])
        # The owner fingerprint binds original status, clocks and source/route,
        # independently of repeated delivery or request clocks. Changed source
        # facts need a new assessment even when the data-problem reason stays
        # the same; episode and notification identity remain separate.
        original_status_facts = sorted(
            {item["fingerprint"] for item in observations if item.get("original") is not None}
        )
        # Reading time, growing ages, repeated status gaps and original-response
        # transport metadata are not the identity of a logical evaluation.
        # Real receipt changes are retained only for the unknown-clock policy.
        return _fingerprint(
            _stable_material(
                {
                    "rule": RULE_KEY,
                    "owner": inputs.owner_basis_id,
                    "route": route,
                    "provider": inputs.saved.provider,
                    "original_status_facts": original_status_facts,
                    "quote": {
                        "bid": decision.bid,
                        "currency": inputs.quote.currency,
                        "original_bid_at": decision.original_bid_at,
                        "receipt_at": (
                            decision.received_at
                            if decision.evaluation_mode == "INDICATIVE_ISSUER"
                            else None
                        ),
                        "mode": decision.evaluation_mode,
                    },
                    "calendar": material.get("review_sessions", {}).get("calendar"),
                    "comparison_calendar": material.get("comparison_sessions", {}).get("calendar"),
                    "scale": {
                        key: value
                        for key, value in material.get("product_scale", {}).items()
                        if key != "review_at"
                    },
                    "outcome": decision.outcome,
                    "reasons": decision.reasons,
                    "review_due": decision.review_due,
                    "review_event_key": IndicativeEntryService._review_event_key(inputs, decision),
                    "review_reasons": (inputs.review_count.reasons if inputs.review_count else ()),
                }
            )
        )

    @staticmethod
    def _review_event_key(inputs: IndicativeInputs, decision: IndicativeDecision) -> str | None:
        if decision.review_due is not True:
            return None
        return _fingerprint(
            {
                "entry": inputs.material.get("entry"),
                "threshold_sessions": 20,
                "twentieth_closes_at": (
                    inputs.review_count.twentieth_closes_at if inputs.review_count else None
                ),
            }
        )

    async def _persist(
        self,
        inputs: IndicativeInputs,
        decision: IndicativeDecision,
        fingerprint: str,
        previous_id: UUID | None,
        duplicate: bool,
        now: datetime,
        notifications_enabled: bool,
    ) -> IndicativeEvaluationResult:
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
        review_key = self._review_event_key(inputs, decision)
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
                    ordering_at=decision.ordering_at,
                    inputs=inputs.material,
                    result=JSON_VALUE.dump_python(
                        {**asdict(decision), "review_event_key": review_key},
                        mode="json",
                    ),
                )
            )
            await session.flush()
        alerts_created = notifications_created = 0
        for kind in EPISODE_KINDS:
            episode = active.get(kind)
            desired = self._desired(kind, decision)
            changed_review = (
                kind == "REVIEW_DUE"
                and desired is True
                and episode is not None
                and episode.event_key != review_key
            )
            if (desired is False or changed_review) and episode is not None:
                episode.closed_at = now
                episode.closing_assessment_id = assessment_id
                episode.close_reason = (
                    "POSITION_CLOSED_OR_CANCELLED"
                    if decision.outcome == "CLOSED"
                    else (
                        "REVIEW_THRESHOLD_CORRECTED"
                        if kind == "REVIEW_DUE"
                        else (
                            "INDICATIVE_PRICE_AVAILABLE"
                            if kind == "DATA_UNAVAILABLE"
                            else "INDICATIVE_BID_AT_OR_ABOVE_GROSS_ENTRY"
                        )
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
                prior_review = (
                    await session.scalar(
                        select(Episode).where(
                            Episode.workspace_id == inputs.workspace_id,
                            Episode.position_id == inputs.position_id,
                            Episode.rule_version == RULE_VERSION,
                            Episode.kind == "REVIEW_DUE",
                            Episode.event_key == review_key,
                        )
                    )
                    if kind == "REVIEW_DUE"
                    else None
                )
                if prior_review is None:
                    episode = await self._open_episode(kind, inputs, decision, assessment_id, now)
                    active[kind] = episode
                    alerts_created += 1
            if episode is not None and episode.closed_at is None and notifications_enabled:
                notifications_created += int(await self._ensure_notification(episode, inputs, now))
        await session.commit()
        return IndicativeEvaluationResult(
            assessment_id,
            decision.outcome,
            decision.reasons,
            duplicate,
            alerts_created,
            notifications_created,
            "DATA_UNAVAILABLE" in active,
            decision.review_due is True,
            "ENTRY_LOSS" in active,
        )

    @staticmethod
    def _desired(kind: EpisodeKind, decision: IndicativeDecision) -> bool | None:
        if decision.outcome == "CLOSED":
            return False
        if kind == "REVIEW_DUE":
            return decision.review_due
        if kind == "DATA_UNAVAILABLE":
            return decision.outcome == "UNAVAILABLE"
        if decision.outcome == "BELOW_ENTRY":
            return True
        if decision.outcome == "AT_OR_ABOVE_ENTRY":
            return False
        # Neither a gap nor a revised/incomplete calendar claims price recovery.
        return None

    async def _open_episode(
        self,
        kind: EpisodeKind,
        inputs: IndicativeInputs,
        decision: IndicativeDecision,
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
        alert_type, reason = {
            "ENTRY_LOSS": (
                AlertType.INDICATIVE_ENTRY_LOSS,
                "Indikativer Geldkurs unter persönlichem Bruttoeinstand nach 20 Sitzungen. "
                "Prüfen; kein nach B04/B58 qualifizierter Verlusthinweis.",
            ),
            "REVIEW_DUE": (
                AlertType.POSITION_REVIEW_DUE,
                "20 abgeschlossene Basiswertsitzungen erreicht. Position prüfen; "
                "diese Erinnerung bestätigt keine Verlustbedingung.",
            ),
            "DATA_UNAVAILABLE": (
                AlertType.POSITION_DATA_UNAVAILABLE,
                "Die indikative Einstandsbeobachtung ist wegen fehlender oder ungeeigneter "
                "Daten nicht beurteilbar. Ein bisheriger Hinweis bleibt davon getrennt.",
            ),
        }[kind]
        alert = Alert(
            id=uuid4(),
            position_id=inputs.position_id,
            trade_id=inputs.trade_id,
            alert_type=alert_type,
            severity=AlertSeverity.WARNING,
            rule_key=f"{RULE_KEY}:{kind}",
            reason=reason,
            observed_value=decision.bid if kind == "ENTRY_LOSS" else None,
            threshold_value=decision.gross_entry if kind == "ENTRY_LOSS" else None,
            market_data_observed_at=(decision.original_bid_at if kind == "ENTRY_LOSS" else None),
            detected_at=now,
            price_context=self._context(inputs, decision, kind, assessment_id, episode_id, now),
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
            event_key=(self._review_event_key(inputs, decision) if kind == "REVIEW_DUE" else None),
            episode_number=sequence,
            opening_assessment_id=assessment_id,
            alert_id=alert.id,
            opened_at=now,
        )
        self._session.add(episode)
        return episode

    @staticmethod
    def _context(
        inputs: IndicativeInputs,
        decision: IndicativeDecision,
        kind: EpisodeKind,
        assessment_id: UUID,
        episode_id: UUID,
        now: datetime,
    ) -> dict[str, str | None]:
        saved, quote = inputs.saved, inputs.saved.quote
        route = saved.route
        context = {
            **status_point_context(inputs.material),
            "scope": RULE_SCOPE,
            "rule_version": RULE_VERSION,
            "qualified_b04": "false",
            "evaluation_mode": decision.evaluation_mode,
            "basis": "WARRANT",
            "price_type": "BID" if decision.bid is not None else None,
            "currency": inputs.material["economic_basis"]["cost_basis_currency"],
            "provider": saved.provider,
            "provider_identity": quote.provider_symbol if quote else None,
            "isin": inputs.material["warrant_isin"],
            "listing_id": str(route.warrant_listing_id) if route else None,
            "venue_mic": route.venue_mic if route else None,
            "source_mode": quote.source_mode if quote else None,
            "quote_time_text": quote.quote_time_text if quote else None,
            "quote_time_basis": quote.quote_time_basis if quote else None,
            "observed_at": (
                decision.original_bid_at.isoformat() if decision.original_bid_at else None
            ),
            "retrieved_at": (decision.received_at.isoformat() if decision.received_at else None),
            "source_freshness": (
                "WITHIN_900_SECONDS"
                if decision.evaluation_mode == "SOURCE_BID"
                else ("UNKNOWN" if decision.evaluation_mode == "INDICATIVE_ISSUER" else None)
            ),
            "completed_sessions": (
                str(decision.completed_sessions)
                if decision.completed_sessions is not None
                else None
            ),
            "session_count_at": decision.session_count_at.isoformat(),
            "session_count_basis": (
                "ORIGINAL_BID" if decision.evaluation_mode == "SOURCE_BID" else "EVALUATION_TIME"
            ),
            "review_completed_sessions": (
                str(decision.review_completed_sessions)
                if decision.review_completed_sessions is not None
                else None
            ),
            "review_session_count_at": now.isoformat(),
            "remaining_quantity": str(decision.remaining_quantity),
            "data_problem_reasons": (
                ",".join(decision.reasons) if kind == "DATA_UNAVAILABLE" else None
            ),
            "episode_id": str(episode_id),
            "assessment_id": str(assessment_id),
            "owner_basis_id": inputs.owner_basis_id,
            "execution_usable": "false",
        }
        return context

    async def _ensure_notification(
        self, episode: Episode, inputs: IndicativeInputs, now: datetime
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
