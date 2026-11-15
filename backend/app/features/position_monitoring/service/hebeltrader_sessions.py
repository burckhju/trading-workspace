"""One database-only snapshot of owner entry and imported session evidence."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    SessionEntry,
    count_completed_sessions,
    session_anchor,
    unavailable_session_count,
)
from app.features.position_monitoring.service.hebeltrader_session_contracts import (
    HebeltraderSessionsReport,
    SessionIssue,
    SessionPeriodView,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.service.hebeltrader_evidence import (
    HebeltraderMonitoringBasis,
    read_hebeltrader_monitoring_basis,
)

REASONS = {
    "EFFECTIVE_ENTRY_MISSING": "Ein effektiver ursprünglicher Kaufbeleg fehlt.",
    "ENTRY_TIME_INVALID": "Der ursprüngliche Kaufzeitbeleg ist unvollständig oder widersprüchlich.",
    "ENTRY_TIMEZONE_INVALID": "Die ursprüngliche Kaufzeitzone ist nicht eindeutig verwendbar.",
    "ENTRY_DATE_INTERVAL_INVALID": (
        "Das ursprüngliche Kaufdatum bildet kein gültiges Zeitintervall."
    ),
    "ENTRY_AFTER_EVALUATION": "Der ursprüngliche Kaufbeleg liegt nach dem Prüfzeitpunkt.",
    "ENTRY_CALENDAR_DAY_AMBIGUOUS": (
        "Das Kaufdatum ohne Uhrzeit umfasst in der Kalenderzeitzone mehrere mögliche Tage. "
        "Eine Kaufuhrzeit wird nicht ergänzt; Tag 0 ist damit noch nicht eindeutig belegt."
    ),
    "ENTRY_OUTSIDE_BINDING_VALIDITY": (
        "Der ursprüngliche Kauftag liegt außerhalb der belegten historischen Kalenderbindung."
    ),
    "EVALUATION_OUTSIDE_BINDING_VALIDITY": (
        "Die historische Kalenderbindung deckt den aktuellen Prüfzeitpunkt nicht ab."
    ),
    "SESSION_BINDING_MISSING": "Eine ausdrücklich gebundene Basiswert-Kalenderevidenz fehlt.",
    "SESSION_EVIDENCE_MISSING": (
        "Für diesen Basiswert ist kein Sitzungsevidenzimport gespeichert. "
        "Benötigt wird ein geprüfter Quellbeleg mit genau zugeordnetem Listing und Zeitraum."
    ),
    "SESSION_LISTING_BINDING_MISMATCH": (
        "Der importierte Kalender passt nicht zur ausdrücklich angefragten Listingbindung."
    ),
    "SESSION_OWNER_BINDING_CHANGED": (
        "Listing oder Handelsplatz stimmen nicht mehr mit der gespeicherten Kalenderbindung "
        "überein. Die historische Zuordnung muss nachvollziehbar geklärt werden."
    ),
    "SESSION_EVIDENCE_WITHDRAWN": (
        "Der letzte Sitzungsevidenzstand wurde ausdrücklich zurückgenommen. "
        "Ein älterer Stand wird nicht automatisch verwendet."
    ),
    "SESSION_BINDING_VALIDITY_GAP": "Die Kalenderbindung deckt den benötigten Zeitraum nicht ab.",
    "SESSION_COVERAGE_RANGE_GAP": (
        "Der Quellbeleg deckt den benötigten Zeitraum nicht vollständig ab."
    ),
    "SESSION_DAY_EVIDENCE_GAP": (
        "Für einzelne Tage fehlen Kalenderbelege. Fehlende Tage gelten nicht als Feiertage."
    ),
    "SESSION_DAY_EVIDENCE_UNKNOWN": (
        "Der Kalender bezeichnet einzelne benötigte Tage als unbekannt."
    ),
    "SESSION_DAYS_MISSING": "Für die vollständige Sitzungszählung fehlen Tagesbelege.",
    "SESSION_DAYS_UNKNOWN": "Unbekannte Kalendertage verhindern eine vollständige Sitzungszählung.",
    "SESSION_DAYS_CONFLICT": (
        "Die gelieferten Sitzungstage sind widersprüchlich oder nicht eindeutig."
    ),
    "SESSION_COUNT_LIMIT": "Der vollständige Zeitraum überschreitet die begrenzte Sitzungszählung.",
    "SESSION_RANGE_LIMIT_EXCEEDED": (
        "Der benötigte Kalenderbereich überschreitet die vollständige Lesegrenze. "
        "Ein gekürzter Ausschnitt wird nicht als vollständige Evidenz verwendet."
    ),
    "POSITION_CLOSED_OR_CANCELLED": (
        "Die Position ist geschlossen oder storniert. "
        "Daraus wird keine aktuelle Fristprüfung abgeleitet."
    ),
}

NOTICES = (
    "Der ursprüngliche Kauftag zählt als Tag 0. Nur spätere dokumentierte Sitzungen nach ihrem "
    "letzten Schluss zählen; Tageskurslücken sind keine Kalenderbelege.",
    "Diese Zählung gilt zum angezeigten serverseitigen Prüfzeitpunkt. B04/B58 benötigen später "
    "die abgeschlossene 20. Basiswertsitzung bereits zur belegten Original-Geldkurszeit, "
    "eine verifizierte offene Produktsitzung und höchstens 900 Sekunden Kursalter.",
    "Der Import bewahrt das Originalmanifest und den Quellbeleg mit dokumentierter menschlicher "
    "Prüfung. Die Software prüft Struktur, Hashes und Bindungen; sie verifiziert die Quelle "
    "nicht unabhängig und bestätigt keinen aktuell offenen Markt.",
    "B04/B05/B06/B58 werden hier nicht ausgewertet. Produktfristen, Z1-bezogene Zählung, "
    "Verlustepisoden, Aktivierung und Zustellung bleiben getrennte Schritte. "
    "Dieser Read bucht keine Ausführung und ruft keinen Provider auf.",
)


def _entry(owner: HebeltraderMonitoringBasis) -> SessionEntry | None:
    first = next(
        (
            fact
            for fact in owner.execution_basis.effective_executions
            if fact.side is ExecutionSide.BUY
        ),
        None,
    )
    if first is None:
        return None
    return SessionEntry(
        execution_id=first.id,
        executed_at=first.executed_at if first.executed_on is None else None,
        executed_on=first.executed_on,
        execution_timezone=first.execution_timezone,
        time_precision="EXACT" if first.executed_on is None else "DATE_ONLY",
    )


def _inconsistent() -> ApplicationError:
    return ApplicationError(
        code="HEBELTRADER_SESSION_READ_INCONSISTENT",
        message="Die Sitzungsevidenz konnte nicht konsistent zur Position gelesen werden.",
        status_code=503,
    )


class HebeltraderSessionReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def _snapshot(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                yield session
            finally:
                await session.rollback()

    async def read(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> HebeltraderSessionsReport:
        started = datetime.now(UTC)
        async with self._snapshot() as session:
            owner = await read_hebeltrader_monitoring_basis(
                session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                lock=False,
            )
            underlying_id = owner.coverage.underlying_id
            reader = SessionEvidenceReader(session)
            current = await reader.current(
                workspace_id=workspace_id,
                instrument_kind="UNDERLYING",
                instrument_id=underlying_id,
                known_at=started,
            )
            if (
                current.workspace_id != workspace_id
                or current.instrument_kind != "UNDERLYING"
                or current.instrument_id != underlying_id
                or current.known_at != started
            ):
                raise _inconsistent()
            entry = _entry(owner)
            position = owner.execution_basis.valuation_basis.position
            state: Literal["OPEN", "CLOSED", "CANCELLED"] = (
                "CANCELLED"
                if position.is_cancelled or owner.execution_basis.trade.cancelled_at is not None
                else "CLOSED" if position.closed_at else "OPEN"
            )
            anchor = session_anchor(entry, current.binding, event_at=started)
            reasons = tuple(dict.fromkeys((*current.reasons, *anchor.reasons)))
            period = SessionPeriodView(None, None, "NOT_REQUESTED", None, (), ())
            if state != "OPEN":
                count = unavailable_session_count(
                    event_at=started,
                    anchor_date=anchor.day,
                    reasons=("POSITION_CLOSED_OR_CANCELLED",),
                    applicable=False,
                )
            elif current.status != "AVAILABLE" or reasons:
                count = unavailable_session_count(
                    event_at=started,
                    anchor_date=anchor.day,
                    reasons=reasons or ("SESSION_BINDING_MISSING",),
                )
            else:
                assert current.binding is not None and anchor.day is not None
                end = started.astimezone(ZoneInfo(current.binding.timezone)).date()
                if end > anchor.day:
                    evidence = await reader.read(
                        workspace_id=workspace_id,
                        instrument_kind="UNDERLYING",
                        instrument_id=underlying_id,
                        start_date=anchor.day + timedelta(days=1),
                        end_date=end,
                        known_at=started,
                        expected_listing_id=current.binding.listing_id,
                    )
                    if (
                        evidence.workspace_id != workspace_id
                        or evidence.instrument_kind != "UNDERLYING"
                        or evidence.instrument_id != underlying_id
                        or evidence.known_at != started
                        or evidence.revision_id != current.revision_id
                        or evidence.binding != current.binding
                        or evidence.source != current.source
                        or evidence.start_date != anchor.day + timedelta(days=1)
                        or evidence.end_date != end
                    ):
                        raise _inconsistent()
                    period = SessionPeriodView(
                        evidence.start_date,
                        evidence.end_date,
                        evidence.status,
                        evidence.fingerprint,
                        evidence.missing_dates,
                        evidence.days,
                    )
                    if evidence.status != "COMPLETE" or evidence.reasons:
                        count = unavailable_session_count(
                            event_at=started,
                            anchor_date=anchor.day,
                            reasons=evidence.reasons or ("SESSION_DAYS_MISSING",),
                        )
                    else:
                        count = count_completed_sessions(
                            entry=entry,
                            binding=current.binding,
                            days=evidence.days,
                            event_at=started,
                        )
                else:
                    count = count_completed_sessions(
                        entry=entry, binding=current.binding, days=(), event_at=started
                    )
            issue_codes = tuple(dict.fromkeys((*current.reasons, *count.reasons)))
            material = {
                "definition": "hebeltrader-sessions-v1",
                "execution_owner_basis": owner.execution_basis.valuation_basis.basis_id,
                "entry": asdict(entry) if entry else None,
                "calendar_revision_id": current.revision_id,
                "period_fingerprint": period.fingerprint,
                "count": asdict(count),
            }
            basis_id = hashlib.sha256(
                json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
            ).hexdigest()
            return HebeltraderSessionsReport(
                trade_id=trade_id,
                position_id=position_id,
                product_id=owner.execution_basis.trade.product_id,
                underlying_id=underlying_id,
                position_state=state,
                basis_id=basis_id,
                read_started_at=started,
                read_completed_at=datetime.now(UTC),
                evaluated_at=started,
                entry=entry,
                calendar=current,
                period=period,
                count=count,
                issues=tuple(
                    SessionIssue(
                        code, REASONS.get(code, f"Sitzungsevidenz ist ungeeignet: {code}.")
                    )
                    for code in issue_codes
                ),
                notices=NOTICES,
            )
