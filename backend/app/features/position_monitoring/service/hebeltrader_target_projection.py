"""Map existing owner facts and immutable target results to a readable contract."""

from datetime import datetime
from typing import Literal

from pydantic import TypeAdapter

from app.features.market_data.service.hebeltrader_history import HebeltraderPriceHistory
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetAssessment,
    TargetDailyEvidence,
    TargetHistoryBasis,
    TargetPositionBasis,
    TargetResult,
    TargetSourceBasis,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import TargetAssessmentRecord
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    BasisStatus,
    OrientationView,
    ProtectionBasisView,
    TargetAssessmentView,
    TargetEvidenceView,
    TargetView,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.service.hebeltrader_evidence import HebeltraderMonitoringBasis

ASSESSMENT_ADAPTER = TypeAdapter(TargetAssessment)
VIEW_ADAPTER = TypeAdapter(TargetAssessmentView)


def target_position(owner: HebeltraderMonitoringBasis) -> TargetPositionBasis:
    coverage = owner.coverage
    basis = owner.execution_basis
    position = basis.valuation_basis.position
    first_buy = next(
        (fact for fact in basis.effective_executions if fact.side is ExecutionSide.BUY), None
    )
    direction: Literal["CALL", "PUT"] | None = None
    if owner.option_direction is not None:
        direction = "CALL" if owner.option_direction.value == "CALL" else "PUT"
    return TargetPositionBasis(
        workspace_id=basis.trade.workspace_id,
        trade_id=basis.trade.id,
        position_id=position.id,
        product_id=basis.trade.product_id,
        underlying_id=coverage.underlying_id,
        owner_basis_id=coverage.basis_id,
        opened_at=first_buy.executed_at if first_buy and first_buy.executed_on is None else None,
        opened_on=first_buy.executed_on if first_buy else None,
        opening_timezone=first_buy.execution_timezone if first_buy else None,
        remaining_quantity=position.open_quantity,
        closed=position.is_closed,
        cancelled=basis.trade.cancelled_at is not None or position.is_cancelled,
        option_direction=direction,
        original_z1_quantity=coverage.original_z1_quantity,
        assigned_z1_sold_quantity=coverage.assigned_z1_sold_quantity,
        personal_underlying_entry=coverage.personal_underlying_entry,
        personal_underlying_binding=(
            PriceBinding(
                PriceBasis.UNDERLYING, coverage.underlying_id, coverage.underlying_currency
            )
            if coverage.underlying_currency is not None
            else None
        ),
        evidence_revision_id=coverage.evidence_revision_id,
    )


def target_source(owner: HebeltraderMonitoringBasis) -> TargetSourceBasis | None:
    source = owner.coverage.source
    if source is None:
        return None
    return TargetSourceBasis(
        source_version_id=source.source_version_id,
        binding=source.underlying.binding,
        scale_reference=owner.scale.source_scale_reference,
        reference_price=source.underlying.reference_price,
        target_1=source.underlying.target_1,
        target_2=source.underlying.target_2,
        content_hash=source.content_hash,
        issue_date=source.issue_date,
    )


def target_history(history: HebeltraderPriceHistory) -> TargetHistoryBasis:
    binding = history.binding
    return TargetHistoryBasis(
        workspace_id=history.workspace_id,
        underlying_id=history.underlying_id,
        fingerprint=history.fingerprint,
        rows=tuple(
            TargetDailyEvidence(
                source_row_id=row.source_row_id,
                fingerprint=row.fingerprint,
                workspace_id=row.workspace_id,
                listing_id=row.listing_id,
                trading_date=row.trading_date,
                high=row.high,
                currency=row.currency,
                interval_start=row.interval_start,
                interval_end=row.interval_end,
                issues=row.issues,
                scale_status=row.scale_status,
            )
            for row in history.rows
        ),
        listing_id=binding.listing_id if binding else None,
        binding=(
            PriceBinding(PriceBasis.UNDERLYING, history.underlying_id, binding.currency)
            if binding
            else None
        ),
        listing_fingerprint=binding.fingerprint if binding else None,
        listing_timezone=binding.timezone if binding else None,
        known_at=history.known_at,
        status=history.status,
        reasons=history.reasons,
        stored_range_complete=history.stored_range_complete,
        intervals_complete=history.intervals_complete,
        start_date=history.start_date,
        end_date=history.end_date,
    )


def persisted_view(record: TargetAssessmentRecord) -> TargetAssessmentView:
    return VIEW_ADAPTER.validate_python(record.result)


def _evidence_view(
    result: TargetResult,
    history: HebeltraderPriceHistory,
    previous: TargetAssessmentRecord | None,
) -> TargetEvidenceView | None:
    proof = result.proof
    if proof is None:
        return None
    evidence = proof.evidence
    row = next(
        (
            row
            for row in history.rows
            if (row.source_row_id, row.fingerprint)
            == (evidence.source_row_id, evidence.fingerprint)
        ),
        None,
    )
    if row is None and previous is not None:
        # A later missing/corrected cache row cannot rewrite the original proof.
        earlier = next(
            item for item in persisted_view(previous).targets if item.target == result.target
        )
        if earlier.evidence is not None and (
            earlier.evidence.source_row_id,
            earlier.evidence.source_fingerprint,
        ) == (evidence.source_row_id, evidence.fingerprint):
            return earlier.evidence
    if row is None or evidence.interval_start is None or evidence.interval_end is None:
        raise ValueError("Target proof has no retained original market provenance")
    return TargetEvidenceView(
        trading_date=evidence.trading_date,
        interval_start=evidence.interval_start,
        interval_end=evidence.interval_end,
        high=evidence.high,
        source_row_id=evidence.source_row_id,
        source_fingerprint=evidence.fingerprint,
        provider=row.provider,
        provider_symbol=row.provider_symbol,
        listing_id=evidence.listing_id,
        time_precision="DATE_ONLY",
        detected_at=proof.detected_at,
    )


def reason_text(reason: str) -> str:
    # Owner/domain reason codes remain available in the immutable audit result.
    return REASON_TEXT.get(reason, f"Ein Vergleichsbeleg erfordert Klärung ({reason}).")


REASON_TEXT: dict[str, str] = {
    "PRODUCT_TERMS_MISSING": "Historische Produktbedingungen und Optionsrichtung fehlen.",
    "PRODUCT_DIRECTION_CONFLICT": "Die dokumentierten Produktbedingungen widersprechen sich.",
    "ADJUSTMENT_INDICATION_PRESENT": "Die Kursdaten enthalten ein ungeklärtes Anpassungsindiz.",
    "ENTRY_TIME_PRECISION_CONFLICT": "Einstiegsdatum und behauptete Uhrzeit widersprechen sich.",
    "ENTRY_TIMEZONE_MISSING": "Zum tagesgenauen Einstieg fehlt die ursprüngliche Zeitzone.",
    "ENTRY_TIMEZONE_INVALID": "Die Zeitzone des Einstiegs ist ungültig.",
    "ENTRY_TIME_MISSING_OR_INVALID": "Der belegte Zeitpunkt des ersten effektiven Kaufs fehlt.",
    "INTERVAL_NOT_ENTIRELY_AFTER_ENTRY": (
        "Das Tagesintervall liegt nicht sicher vollständig nach dem Kauf."
    ),
    "PRODUCT_DIRECTION_NOT_SUPPORTED": (
        "Die bestätigte CALL-Aufwärtskonstellation ist für dieses Produkt nicht belegt; "
        "PUT-Ziele werden in diesem Schnitt nicht ausgewertet."
    ),
    "SOURCE_BASIS_MISSING": "Die passende bestätigte historische Hebeltrader-Quelle fehlt.",
    "SOURCE_PRICE_BINDING_MISMATCH": (
        "Preisachse, Basiswert oder Währung der Quelle passen nicht zur Position."
    ),
    "SOURCE_CALL_TARGET_ORDER_INVALID": (
        "Referenz, Z1 und Z2 belegen keine gültige aufsteigende CALL-Zielkonstellation."
    ),
    "SOURCE_SCALE_REFERENCE_MISSING": (
        "Die Referenz für den Preismaßstab der historischen Quelle fehlt."
    ),
    "SOURCE_ISSUE_DATE_MISSING": "Das belegte Ausgabedatum der Quelle fehlt.",
    "SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED": (
        "Der Kursbeleg liegt nicht sicher nach der Veröffentlichung dieser Quellenversion; "
        "Publikationsuhrzeit und Verlagszeitzone sind unbekannt."
    ),
    "HISTORY_SCOPE_MISMATCH": "Die Kursreihe gehört zu einem anderen Workspace oder Basiswert.",
    "HISTORY_MISSING": "Für den benötigten Bereich sind keine gespeicherten Kurse verfügbar.",
    "HISTORY_BLOCKED": "Die historische Kursbindung ist widersprüchlich oder unvollständig.",
    "HISTORY_LIMIT_EXCEEDED": (
        "Die Kursreihe überschreitet die vollständige Lesegrenze; es wird keine verkürzte "
        "Reihe bewertet."
    ),
    "STORED_HISTORY_RANGE_INCOMPLETE": (
        "Der gespeicherte Kursbereich konnte nicht vollständig gelesen werden."
    ),
    "HISTORICAL_LISTING_BINDING_MISSING": (
        "Die historische Zuordnung zu Listing und Handelsplatz fehlt."
    ),
    "HISTORY_PRICE_BINDING_MISMATCH": (
        "Preisachse, Basiswert oder Währung der Kurse passen nicht zur Quelle."
    ),
    "LISTING_TIMEZONE_MISSING": "Die Listing-Zeitzone für das Tagesintervall fehlt.",
    "LISTING_TIMEZONE_INVALID": "Die Listing-Zeitzone für das Tagesintervall ist ungültig.",
    "HISTORY_CUTOFF_INVALID": (
        "Der Zeitstand der Kursreihe ist nicht eindeutig oder liegt nach der Prüfung."
    ),
    "PRICE_COMPARISON_NOT_CONFIRMED": (
        "Historische Listingbindung und unveränderter Vergleichsmaßstab dieser Kursreihe sind"
        " noch nicht ausdrücklich mit einer Belegreferenz qualifiziert."
    ),
    "COMPARISON_HISTORY_FINGERPRINT_MISMATCH": (
        "Die Vergleichsfreigabe gehört zu einem anderen Stand der Kursreihe."
    ),
    "COMPARISON_LISTING_FINGERPRINT_MISMATCH": (
        "Die Vergleichsfreigabe gehört zu einem anderen Stand der Listingbindung."
    ),
    "COMPARISON_SOURCE_VERSION_MISMATCH": (
        "Die Vergleichsfreigabe gehört zu einer anderen historischen Quellenversion."
    ),
    "COMPARISON_SCALE_REFERENCE_MISMATCH": (
        "Die Vergleichsfreigabe verwendet einen anderen Preismaßstab."
    ),
    "COMPARISON_EVIDENCE_REFERENCE_MISSING": "Der konkrete Beleg für die Vergleichsfreigabe fehlt.",
    "CONFLICTING_ORIGINAL_PRICE_EVIDENCE": (
        "Mehrere Originalkursbelege widersprechen sich in ihrer Identität."
    ),
    "ROW_SCOPE_OR_CURRENCY_MISMATCH": (
        "Ein Kursbeleg gehört zu einem anderen Workspace, Listing oder einer anderen Währung."
    ),
    "ROW_EVIDENCE_UNSUITABLE": (
        "Ein Kursbeleg hat ein ausdrücklich ausgewiesenes Zeit-, Qualitäts- oder "
        "Identitätsproblem."
    ),
    "ROW_ADJUSTMENT_REQUIRES_OWNER_EVIDENCE": (
        "Ein Anpassungsindiz erfordert verifizierte Anpassungsbelege des zuständigen "
        "Datenowners; eine pauschale Skalenfreigabe reicht nicht aus."
    ),
    "ROW_ORIGINAL_VALUES_INVALID": (
        "Originalwert oder Originalreferenz des Kursbelegs ist ungültig."
    ),
    "FULL_DAILY_INTERVAL_NOT_ESTABLISHED": (
        "Das vollständige lokale Tagesintervall ist nicht belegt."
    ),
    "FULL_DAILY_INTERVAL_NOT_COMPLETED": (
        "Das vollständige lokale Tagesintervall war zum Prüfzeitstand noch nicht beendet."
    ),
    "ROW_OUTSIDE_REQUESTED_RANGE": (
        "Ein Kursbeleg liegt außerhalb des angefragten historischen Bereichs."
    ),
    "NO_SUITABLE_POST_ENTRY_DAILY_EVIDENCE": (
        "Kein geeigneter abgeschlossener Tagesbeleg liegt sicher nach dem Einstieg vor."
    ),
    "PROVEN_SOURCE_BASIS_UNAVAILABLE": (
        "Die Quelle des ursprünglichen Zielnachweises ist aktuell nicht qualifizierbar; den "
        "Originalbeleg klären."
    ),
    "PROVEN_SOURCE_BASIS_CHANGED": (
        "Quellenversion, Marken oder Maßstab haben sich gegenüber dem ursprünglichen "
        "Zielnachweis geändert."
    ),
    "PROVEN_ENTRY_TIME_BASIS_CHANGED": (
        "Die Kaufzeit wurde gegenüber dem ursprünglichen Zielnachweis korrigiert; die "
        "damalige Reihenfolge ist neu zu klären."
    ),
    "PROVEN_PRODUCT_DIRECTION_CHANGED": (
        "Die Produktbedingungen ändern die Richtung des ursprünglichen Zielnachweises."
    ),
    "PROVEN_LISTING_BASIS_CHANGED": (
        "Die Listingbindung des ursprünglichen Zielnachweises wurde geändert."
    ),
    "ORIGINAL_PRICE_EVIDENCE_CHANGED": (
        "Der ursprüngliche Kursbeleg wurde korrigiert. Sein früherer Stand bleibt erhalten "
        "und erfordert Klärung."
    ),
    "ORIGINAL_PRICE_EVIDENCE_REPLACED": (
        "Der ursprüngliche Kursbeleg wurde durch eine andere Originalzeile ersetzt; die "
        "Zuordnung muss geklärt werden."
    ),
    "PRIOR_REVIEW_REQUIRED": (
        "Eine frühere Korrekturklärung ist noch offen; eine weitere normale Prüfung hebt sie "
        "nicht auf."
    ),
    "ORIGINAL_Z1_QUANTITY_MISSING_OR_INVALID": (
        "Die vollständig belegte ursprüngliche Einstiegsgruppe und ihr Z1-Mengenbezug fehlen."
    ),
    "Z1_SALE_ATTRIBUTION_MISSING_OR_INVALID": (
        "Die ausdrückliche Prüfung beziehungsweise Zuordnung tatsächlicher Z1-Verkäufe fehlt."
    ),
    "PERSONAL_UNDERLYING_ENTRY_MISSING_OR_INVALID": (
        "Geeignete Basiswertbelege für alle noch gewichteten Käufe fehlen."
    ),
    "PERSONAL_UNDERLYING_BINDING_MISMATCH": (
        "Preisachse, Basiswert oder Währung des persönlichen Einstands passen nicht zur "
        "Zielquelle."
    ),
    "POSITION_CLOSED_OR_CANCELLED": (
        "Die Position ist geschlossen oder storniert; es entsteht keine neue " "Handlungsableitung."
    ),
    "MARKET_DATA_INSTRUMENT_SCOPE_MISMATCH": (
        "Die zusätzliche Dateninstrument-Zuordnung widerspricht dem Workspace oder Listing "
        "des Originalkurses."
    ),
    "LISTING_TIMEZONE_UNAVAILABLE": "Eine verwendbare Listing-Zeitzone ist nicht gespeichert.",
    "FULL_LOCAL_DAY_NOT_COMPLETED_AT_CUTOFF": (
        "Der lokale Kalendertag war zum Prüfzeitstand noch nicht vollständig beendet."
    ),
    "PRICE_TYPE_NOT_EOD": "Der gespeicherte Kurs ist kein Tageskursbeleg.",
    "EOD_QUALITY_LIMITED": "Qualitätsstatus oder Warnungen schränken den Tageskursbeleg ein.",
    "INVALID_ORIGINAL_VALUES": (
        "Die Originalwerte des Tageskurses sind widersprüchlich oder ungültig."
    ),
    "INVALID_ORIGINAL_SOURCE_BINDING": (
        "Originalwährung oder Providersymbol des Tageskurses ist ungültig."
    ),
    "DATA_NOT_KNOWN_AT_CUTOFF": "Der Kursbeleg war zum Prüfzeitstand noch nicht bekannt.",
    "INVALID_STORED_TIME_ORDER": (
        "Quellaktualisierung, Abruf und Speicherung des Kursbelegs haben eine "
        "widersprüchliche Zeitfolge."
    ),
    "NO_UNIQUE_ACTIVE_PRIMARY_LISTING": (
        "Ein eindeutiges bestehendes Primary-Listing fehlt; es wird kein Handelsplatz " "geraten."
    ),
    "LISTING_IDENTITY_NOT_FOUND": (
        "Das gebundene Listing ist für diesen Workspace und Basiswert nicht verfügbar."
    ),
    "CURRENT_REFERENCE_NOT_KNOWN_AT_CUTOFF": (
        "Die aktuelle Listingreferenz war zum Prüfzeitstand noch nicht bekannt."
    ),
    "HISTORICAL_RANGE_ROW_LIMIT_EXCEEDED": (
        "Der Kursbereich überschreitet 5.000 Zeilen und wird nicht still gekürzt."
    ),
    "NO_STORED_EOD_IN_RANGE": "Im benötigten Bereich sind keine Tageskurse gespeichert.",
}


def _basis_status(status: str) -> BasisStatus:
    if status in {"READY", "COVERED"}:
        return "AVAILABLE"
    if status in {"NOT_TRIGGERED", "POSITION_CLOSED"}:
        return "NOT_APPLICABLE"
    return "NOT_ASSESSABLE"


def assessment_view(
    assessment: TargetAssessment,
    *,
    basis_id: str,
    source: TargetSourceBasis | None,
    history: HebeltraderPriceHistory,
    previous: TargetAssessmentRecord | None,
    recorded_at: datetime,
) -> TargetAssessmentView:
    targets: list[TargetView] = []
    for result in (assessment.z1, assessment.z2):
        historical_source = result.proof.source if result.proof else source
        threshold = None
        if historical_source is not None:
            threshold = (
                historical_source.target_1 if result.target == "Z1" else historical_source.target_2
            )
        details = {
            "PROVEN": (
                "Ziel durch einen qualifizierten Tageshöchstkurs nach dem Einstieg "
                "nachweislich erreicht."
            ),
            "NOT_PROVEN": (
                "In den verfügbaren geeigneten Belegen ist kein Zieltreffer nachgewiesen. Die"
                " gesamte Kurshistorie ist damit nicht als lückenlos geprüft."
            ),
            "NOT_ASSESSABLE": "Die vorhandenen Belege erlauben noch keinen sicheren Zielvergleich.",
            "REVIEW_REQUIRED": (
                "Ein ursprünglicher Zielbeleg bleibt erhalten; geänderte oder "
                "widersprüchliche Grundlagen erfordern eine erneute fachliche Klärung."
            ),
        }
        detail = details[result.status]
        if result.target == "Z2" and assessment.z2_exit_review.status == "READY":
            detail += (
                " Der Ausstieg der Restposition ist zu prüfen; eine Verkaufsausführung ist "
                "damit nicht belegt."
            )
        if result.current_assessability == "NOT_ASSESSABLE" and result.status == "PROVEN":
            detail += (
                " Die aktuelle Eingangsreihe ist nicht vollständig vergleichbar; der frühere "
                "Zielbeleg bleibt gültig."
            )
        targets.append(
            TargetView(
                target=result.target,
                status=result.status,
                threshold=threshold,
                currency=historical_source.binding.currency if historical_source else None,
                event_id=result.event_id if result.proof else None,
                proof_source_version_id=(
                    result.proof.source.source_version_id if result.proof else None
                ),
                proof_scale_reference=result.proof.source.scale_reference if result.proof else None,
                detail=detail,
                reasons=tuple(
                    dict.fromkeys(
                        reason_text(item) for item in (*result.reasons, *result.review_reasons)
                    )
                ),
                evidence=_evidence_view(result, history, previous),
            )
        )
    orientation = assessment.z1_orientation
    orientation_detail = {
        "READY": (
            "Einmalige 50-%-Orientierung auf die belegte ursprüngliche Einstiegsgruppe. Die "
            "konkrete Verkaufsmenge ist ausdrücklich festzulegen."
        ),
        "COVERED": (
            "Die ausdrücklich zugeordneten tatsächlichen Z1-Verkäufe decken die ursprüngliche"
            " 50-%-Orientierung ab."
        ),
        "NOT_TRIGGERED": "Ohne belegten Z1-Treffer entsteht noch keine Verkaufsorientierung.",
        "POSITION_CLOSED": (
            "Die Position ist geschlossen; es entsteht keine neue Verkaufsorientierung."
        ),
        "REVIEW_REQUIRED": (
            "Der historische Zielbeleg muss geklärt werden, bevor die Z1-Orientierung "
            "verwendet wird."
        ),
        "NOT_ASSESSABLE": (
            "Zielbeleg, ursprünglicher Mengenbezug oder ausdrückliche Zuordnung der "
            "Z1-Verkäufe ist noch unvollständig."
        ),
    }[orientation.status]
    protection = assessment.protection_basis
    protection_detail = {
        "READY": (
            "Persönlicher Basiswerteinstand aus den bestehenden Restmengen- und "
            "Kostenbeiträgen. Prüfgrundlage, noch kein bekanntgegebener Schutzvorschlag."
        ),
        "COVERED": (
            "Die persönliche Einstandsgrundlage ist dokumentiert; hieraus wird kein "
            "Schutzvorschlag bekanntgegeben."
        ),
        "NOT_TRIGGERED": (
            "Ohne belegten Z1-Treffer entsteht hier noch kein Anlass für den Einstandsschutz."
            " Vorhandene Kaufbelege bleiben davon unberührt."
        ),
        "POSITION_CLOSED": (
            "Die Position ist geschlossen; es entsteht kein neuer Anlass für den "
            "Einstandsschutz."
        ),
        "REVIEW_REQUIRED": (
            "Der historische Zielbeleg muss geklärt werden, bevor eine "
            "Einstandsschutz-Prüfgrundlage daraus abgeleitet wird."
        ),
        "NOT_ASSESSABLE": (
            "Zielnachweis oder persönlicher Basiswerteinstand ist noch nicht ausreichend "
            "belegt. Die konkrete Lücke steht in der Belegabdeckung beziehungsweise im "
            "Zielbefund."
        ),
    }[protection.status]
    protection_detail += (
        " Bekanntgabe, höherer Schutzboden und Stopüberwachung gehören zum folgenden "
        "F207-2-Schnitt."
    )
    return TargetAssessmentView(
        id=assessment.assessment_id,
        recorded_at=recorded_at,
        basis_id=basis_id,
        source_version_id=source.source_version_id if source else None,
        previous_assessment_id=assessment.previous_assessment_id,
        targets=tuple(targets),
        orientation=OrientationView(
            status=_basis_status(orientation.status),
            original_quantity=orientation.original_quantity,
            assigned_sold_quantity=orientation.assigned_sold_quantity,
            detail=orientation_detail,
        ),
        protection_basis=ProtectionBasisView(
            status=_basis_status(protection.status),
            personal_underlying_entry=protection.personal_underlying_entry,
            currency=protection.binding.currency if protection.binding else None,
            detail=protection_detail,
        ),
    )
