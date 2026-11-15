"""Passive prerequisite read, pinned to one execution/quote/calendar snapshot."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.position_monitoring.domain.hebeltrader_original_bid import assess_original_bid
from app.features.position_monitoring.service.hebeltrader_original_bid_checks import input_checks
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    HebeltraderOriginalBidReport,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_sessions import (
    inconsistent_read,
    product_sessions,
    underlying_sessions,
)
from app.features.position_monitoring.service.hebeltrader_sessions import _entry
from app.features.trade_position.service.hebeltrader_evidence import (
    read_hebeltrader_monitoring_basis,
)

NOTICES = (
    "Die Anzeige prüft gespeicherte Eingangsbelege zum angezeigten Lesestand. Sie berechnet "
    "keinen Einstandsverlust, keine B04-Verlustepisode und kein Verkaufssignal. "
    "B04/B05/B06/B58, Regelaktivierung und Zustellung bleiben unimplementierte Folgeschritte.",
    "Die 20. Basiswertsitzung muss bereits zur ausdrücklichen Original-Geldkurszeit "
    "abgeschlossen sein. Die separate Sitzungsanzeige zum Serverlesezeitpunkt hat einen "
    "anderen Zeitbezug. Empfang, spätere Erfassung und nominelle Feedverzögerung ersetzen "
    "weder Originalzeit noch die Grenze von höchstens 900 Sekunden.",
    "Kalenderbelege stammen aus dokumentierter menschlicher Quellenprüfung. Dokumentierte "
    "Handelsintervalle und Quellstatus OPEN belegen keine unabhängig verifizierte aktuell "
    "offene Produktsitzung. Der historische Optionsschein-Preismaßstab ist ebenfalls offen.",
    "Gelesen wird der veränderliche letzte gespeicherte Erfolg der aktuell bestätigten "
    "Kursroute. Dies ist keine historische Kursrekonstruktion und keine Aussage über einen "
    "späteren Abrufversuch. Ein Speicherdatum wird in diesem Store nicht aufgezeichnet; "
    "es wird nicht aus der Abrufzeit ergänzt.",
    "Dieser Read bucht keine Ausführung, ändert keine Eingaben, aktiviert keine Regel und "
    "löst weder Zustellung noch Providerabfrage aus. Produktive Betriebsbelege stehen aus.",
)


class HebeltraderOriginalBidReader:
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
    ) -> HebeltraderOriginalBidReport:
        started = datetime.now(UTC)
        async with self._snapshot() as session:
            owner = await read_hebeltrader_monitoring_basis(
                session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                lock=False,
            )
            basis = owner.execution_basis
            economic = basis.valuation_basis
            position = economic.position
            if (
                basis.trade.workspace_id != workspace_id
                or basis.trade.id != trade_id
                or position.id != position_id
                or position.trade_id != trade_id
                or position.product_id != basis.trade.product_id
            ):
                raise inconsistent_read()
            state: Literal["OPEN", "CLOSED", "CANCELLED"] = (
                "CANCELLED"
                if position.is_cancelled or basis.trade.cancelled_at is not None
                else "CLOSED" if position.is_closed else "OPEN"
            )
            saved = await RiskMarketDataReader(session).saved_quote(
                workspace_id=workspace_id,
                position_id=position_id,
                as_of=started,
                expected_warrant_id=basis.trade.product_id,
            )
            if saved.route is not None and (
                saved.route.workspace_id != workspace_id
                or saved.route.position_id != position_id
                or saved.route.warrant_id != basis.trade.product_id
                or (saved.provenance is not None and saved.provenance.read_at != started)
            ):
                raise inconsistent_read()
            bid = assess_original_bid(saved, evaluated_at=started, applicable=state == "OPEN")
            calendars = SessionEvidenceReader(session)
            entry = _entry(owner)
            product = await product_sessions(calendars, route=saved.route, bid=bid, now=started)
            underlying = await underlying_sessions(
                calendars,
                workspace_id=workspace_id,
                underlying_id=owner.coverage.underlying_id,
                entry=entry,
                bid=bid,
                now=started,
            )
            checks = input_checks(
                economic=economic,
                saved=saved,
                bid=bid,
                product=product,
                underlying=underlying,
                applicable=state == "OPEN",
            )
            material = {
                "definition": "hebeltrader-original-bid-v1",
                "execution_owner_basis": economic.basis_id,
                "entry": asdict(entry) if entry else None,
                "saved_quote": asdict(saved),
                "bid": asdict(bid),
                "product_sessions": asdict(product),
                "underlying_sessions": asdict(underlying),
                "checks": [asdict(check) for check in checks],
            }
            basis_id = hashlib.sha256(
                json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
            ).hexdigest()
            return HebeltraderOriginalBidReport(
                trade_id=trade_id,
                position_id=position_id,
                product_id=basis.trade.product_id,
                underlying_id=owner.coverage.underlying_id,
                position_state=state,
                basis_id=basis_id,
                read_started_at=started,
                read_completed_at=datetime.now(UTC),
                evaluated_at=started,
                economic_basis=economic,
                entry=entry,
                saved_quote=saved,
                bid=bid,
                product_sessions=product,
                underlying_sessions=underlying,
                coverage_status=(
                    "NOT_APPLICABLE"
                    if state != "OPEN"
                    else (
                        "UNSUITABLE"
                        if any(check.status == "UNSUITABLE" for check in checks)
                        else "PARTIAL"
                    )
                ),
                checks=checks,
                notices=NOTICES,
            )
