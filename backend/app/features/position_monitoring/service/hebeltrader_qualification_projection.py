"""A review of stored comparison inputs, never a new target assessment."""

from app.features.market_data.service.hebeltrader_history import HebeltraderPriceHistory
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
    TargetPositionBasis,
    TargetSourceBasis,
    review_hebeltrader_target_inputs,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import TargetAssessmentRecord
from app.features.position_monitoring.service.hebeltrader_qualification_contracts import (
    StoredTargetQualification,
    TargetQualificationBinding,
    TargetQualificationEntry,
    TargetQualificationIssue,
    TargetQualificationPreview,
    TargetQualificationReadiness,
    TargetQualificationRowReview,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
)
from app.features.position_monitoring.service.hebeltrader_target_projection import (
    reason_text,
    target_history,
)
from app.features.trade_position.service.hebeltrader_evidence import HebeltraderMonitoringBasis

QUALIFICATION_NOTICES = (
    "Die Vergleichsbestätigung ist eine ausdrückliche Nutzererklärung mit konkreter "
    "Belegreferenz. Die Software prüft die technischen Zuordnungen; sie verifiziert "
    "den externen Nachweis nicht unabhängig und ruft ihn nicht automatisch ab.",
    "Aktuelle Listing- und Handelsplatzdaten belegen keine historische Gültigkeit. "
    "Die Währung gespeicherter Kurse kann aus dem Listingkontext übernommen sein; "
    "übereinstimmende Währungen sind deshalb keine unabhängigen Nachweise. Auch "
    "VALID und eine technisch geprüfte Providerzuordnung belegen keinen historischen Maßstab.",
    "Tagesdaten behalten ihre Tagesgenauigkeit. Der vollständig gelesene gespeicherte "
    "Bereich belegt weder vollständige Handelssitzungen noch einen Intraday-Trade zum Kauf.",
    "Die Erklärung betrifft genau diese historische Quelle und den vollständig benannten "
    "gespeicherten Kursbestand. Ungeeignete Einzelbelege bleiben gesperrt; frühere "
    "Klärungsfälle werden dadurch nicht freigegeben. Die Baseline wird nicht aktiviert.",
)

SOURCE_ISSUES = {
    "NOT_FOUND": "Die zugeordnete historische Quellenversion ist in diesem Workspace nicht lesbar.",
    "NOT_CONFIRMED_PDF": (
        "Die zugeordnete Quelle ist kein bestätigter, geeigneter Hebeltrader-PDF-Import."
    ),
    "IDENTITY_MISMATCH": "Produkt und Basiswert der historischen Quelle passen nicht zur Position.",
    "PROVENANCE_MISMATCH": "Versions-, Datei- und Importherkunft der Quelle passen nicht zusammen.",
    "INVALID_MARKS": "Achsen, Währungen oder Marken der historischen Quelle sind ungeeignet.",
}


def _issues(codes: tuple[str, ...]) -> tuple[TargetQualificationIssue, ...]:
    return tuple(TargetQualificationIssue(code, reason_text(code)) for code in codes)


def build_qualification_preview(
    *,
    report: HebeltraderTargetsReport,
    owner: HebeltraderMonitoringBasis,
    position: TargetPositionBasis,
    source: TargetSourceBasis | None,
    history: HebeltraderPriceHistory,
    latest: TargetAssessmentRecord | None,
    qualification: TargetComparisonQualification | None,
) -> TargetQualificationPreview:
    review = review_hebeltrader_target_inputs(
        position=position,
        source=source,
        history=target_history(history),
        as_of=history.known_at,
    )
    readiness = TargetQualificationReadiness(
        status=(
            "NOT_APPLICABLE"
            if "POSITION_CLOSED_OR_CANCELLED" in review.global_reasons
            else "BLOCKED" if review.global_reasons else "REVIEWABLE"
        ),
        issues=_issues(review.global_reasons),
        usable_row_count=review.usable_row_count,
        rows=tuple(
            TargetQualificationRowReview(
                source_row_id=row.source_row_id,
                fingerprint=row.fingerprint,
                status="SUITABLE_AFTER_CONFIRMATION" if row.usable else "UNSUITABLE",
                issues=_issues(row.reasons),
            )
            for row in review.rows
        ),
    )
    binding = None
    if readiness.status == "REVIEWABLE":
        # These invariants were checked by the shared domain input review.
        assert source is not None and source.scale_reference is not None
        assert history.binding is not None
        binding = TargetQualificationBinding(
            history_fingerprint=history.fingerprint,
            listing_fingerprint=history.binding.fingerprint,
            source_version_id=source.source_version_id,
            source_scale_reference=source.scale_reference,
        )
    return TargetQualificationPreview(
        report=report,
        entry=TargetQualificationEntry(
            product_id=position.product_id,
            underlying_id=position.underlying_id,
            option_direction=position.option_direction,
            opened_at=position.opened_at,
            opened_on=position.opened_on,
            opening_timezone=position.opening_timezone,
            evidence_revision_id=position.evidence_revision_id,
        ),
        source=owner.coverage.source,
        attempted_source_version_id=(
            owner.source_evidence.source_version_id if owner.source_evidence else None
        ),
        source_issues=(
            tuple(
                TargetQualificationIssue(code, SOURCE_ISSUES.get(code, reason_text(code)))
                for code in owner.source_evidence.reasons
            )
            if owner.source_evidence
            else ()
        ),
        source_scale=owner.scale,
        history=history,
        readiness=readiness,
        qualification=StoredTargetQualification(
            status=(
                "MISSING"
                if qualification is None
                else "REUSABLE" if report.inputs.qualification_reusable else "STALE"
            ),
            value=qualification,
            contained_in_assessment_id=(latest.id if latest and qualification else None),
            contained_in_recorded_at=(latest.recorded_at if latest and qualification else None),
        ),
        qualification_binding=binding,
        notices=QUALIFICATION_NOTICES,
    )
